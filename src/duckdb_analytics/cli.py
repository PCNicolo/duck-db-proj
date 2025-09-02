#!/usr/bin/env python3
"""Command-line interface for DuckDB Analytics."""

import sys
from pathlib import Path

import click
from tabulate import tabulate

from .core.connection import DuckDBConnection
from .core.query_engine import QueryEngine
from .data.file_manager import FileManager


@click.group()
@click.option("--database", "-d", default="analytics.db", help="Database file path")
@click.pass_context
def main(ctx, database):
    """DuckDB Analytics CLI - Query and explore data files."""
    ctx.ensure_object(dict)
    ctx.obj["connection"] = DuckDBConnection(database)
    ctx.obj["query_engine"] = QueryEngine(ctx.obj["connection"])
    ctx.obj["file_manager"] = FileManager()


@main.command()
@click.argument("query")
@click.option(
    "--output", "-o", type=click.Choice(["table", "json", "csv"]), default="table"
)
@click.option("--limit", "-l", type=int, help="Limit number of rows")
@click.pass_context
def query(ctx, query, output, limit):
    """Execute a SQL query."""
    try:
        # Add limit if specified
        if limit and "limit" not in query.lower():
            query = f"{query} LIMIT {limit}"

        # Execute query
        df = ctx.obj["query_engine"].execute_query(query)

        # Output results
        if output == "table":
            click.echo(tabulate(df, headers="keys", tablefmt="grid", showindex=False))
        elif output == "json":
            click.echo(df.to_json(orient="records", indent=2))
        elif output == "csv":
            click.echo(df.to_csv(index=False))

        # Show row count
        click.echo(f"\n{len(df)} rows returned", err=True)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("filepath", type=click.Path(exists=True))
@click.option("--table-name", "-t", help="Table name (default: filename)")
@click.pass_context
def load(ctx, filepath, table_name):
    """Load a CSV or Parquet file into DuckDB."""
    filepath = Path(filepath)

    if not table_name:
        table_name = filepath.stem.replace(" ", "_").replace("-", "_")

    try:
        if filepath.suffix.lower() == ".csv":
            ctx.obj["connection"].register_csv(str(filepath), table_name)
            click.echo(f"✓ Loaded CSV file as table: {table_name}")
        elif filepath.suffix.lower() in [".parquet", ".parq"]:
            ctx.obj["connection"].register_parquet(str(filepath), table_name)
            click.echo(f"✓ Loaded Parquet file as table: {table_name}")
        else:
            click.echo(f"Error: Unsupported file format {filepath.suffix}", err=True)
            sys.exit(1)

        # Show table info
        info = ctx.obj["connection"].get_table_info(table_name)
        click.echo(f"  Rows: {info['row_count']:,}")
        click.echo(f"  Columns: {len(info['columns'])}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.pass_context
def tables(ctx):
    """List all available tables."""
    try:
        tables = ctx.obj["connection"].list_tables()

        if not tables:
            click.echo("No tables found in database")
            return

        click.echo("Available tables:")
        for table in tables:
            try:
                info = ctx.obj["connection"].get_table_info(table)
                click.echo(
                    f"  • {table:<30} ({info['row_count']:,} rows, {len(info['columns'])} columns)"
                )
            except:
                click.echo(f"  • {table}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("table_name")
@click.pass_context
def describe(ctx, table_name):
    """Describe a table's schema."""
    try:
        info = ctx.obj["connection"].get_table_info(table_name)

        click.echo(f"\nTable: {table_name}")
        click.echo(f"Rows: {info['row_count']:,}\n")

        # Format column information
        columns_data = []
        for col in info["columns"]:
            columns_data.append(
                [
                    col["name"],
                    col["type"],
                    "YES" if col["null"] else "NO",
                    col["key"] if col["key"] else "",
                ]
            )

        click.echo(
            tabulate(
                columns_data,
                headers=["Column", "Type", "Nullable", "Key"],
                tablefmt="grid",
            )
        )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("table_name")
@click.option("--rows", "-n", default=10, help="Number of rows to preview")
@click.pass_context
def preview(ctx, table_name, rows):
    """Preview data from a table."""
    try:
        query = f"SELECT * FROM {table_name} LIMIT {rows}"
        df = ctx.obj["query_engine"].execute_query(query)

        click.echo(f"\nPreview of {table_name} (first {rows} rows):\n")
        click.echo(tabulate(df, headers="keys", tablefmt="grid", showindex=False))

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("table_name")
@click.pass_context
def stats(ctx, table_name):
    """Show statistics for a table."""
    try:
        # Get numeric columns
        query = f"SELECT * FROM {table_name} LIMIT 1"
        df = ctx.obj["query_engine"].execute_query(query)
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

        if not numeric_cols:
            click.echo("No numeric columns found in table")
            return

        # Build stats query
        stats_parts = []
        for col in numeric_cols:
            stats_parts.extend(
                [
                    f"MIN({col}) as {col}_min",
                    f"MAX({col}) as {col}_max",
                    f"AVG({col}) as {col}_avg",
                    f"STDDEV({col}) as {col}_std",
                ]
            )

        stats_query = f"SELECT {', '.join(stats_parts[:20])} FROM {table_name}"  # Limit to prevent too wide output
        stats_df = ctx.obj["query_engine"].execute_query(stats_query)

        # Format and display
        click.echo(f"\nStatistics for {table_name}:\n")

        for col in numeric_cols[:5]:  # Show first 5 numeric columns
            click.echo(f"{col}:")
            if f"{col}_min" in stats_df.columns:
                click.echo(f"  Min: {stats_df[f'{col}_min'].iloc[0]:.2f}")
                click.echo(f"  Max: {stats_df[f'{col}_max'].iloc[0]:.2f}")
                click.echo(f"  Avg: {stats_df[f'{col}_avg'].iloc[0]:.2f}")
                click.echo(f"  Std: {stats_df[f'{col}_std'].iloc[0]:.2f}")
            click.echo()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--directory", "-d", type=click.Path(exists=True), default=".")
@click.pass_context
def scan(ctx, directory):
    """Scan directory for data files."""
    try:
        files = ctx.obj["file_manager"].scan_directory(Path(directory))

        if not files:
            click.echo("No data files found")
            return

        click.echo(f"\nFound {len(files)} data files:\n")

        for file in files:
            size_mb = file["size"] / (1024 * 1024)
            click.echo(f"• {file['name']}")
            click.echo(f"  Format: {file['format'].upper()}")
            click.echo(f"  Size: {size_mb:.2f} MB")
            if file["rows"]:
                click.echo(f"  Rows: {file['rows']:,}")
            click.echo()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("csv_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output parquet file")
@click.pass_context
def convert(ctx, csv_file, output):
    """Convert CSV to Parquet format."""
    try:
        csv_path = Path(csv_file)

        if not output:
            output = csv_path.with_suffix(".parquet")

        output_path = ctx.obj["file_manager"].convert_csv_to_parquet(csv_path, output)

        # Compare file sizes
        csv_size = csv_path.stat().st_size / (1024 * 1024)
        parquet_size = output_path.stat().st_size / (1024 * 1024)
        compression_ratio = (1 - parquet_size / csv_size) * 100

        click.echo(f"✓ Converted {csv_path.name} to {output_path.name}")
        click.echo(f"  CSV size: {csv_size:.2f} MB")
        click.echo(f"  Parquet size: {parquet_size:.2f} MB")
        click.echo(f"  Compression: {compression_ratio:.1f}%")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("query")
@click.pass_context
def explain(ctx, query):
    """Show query execution plan."""
    try:
        plan = ctx.obj["query_engine"].explain_query(query)
        click.echo("\nQuery Execution Plan:\n")
        click.echo(plan)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.pass_context
def interactive(ctx):
    """Start interactive query mode."""
    click.echo("DuckDB Interactive Mode")
    click.echo("Type 'exit' or 'quit' to leave")
    click.echo("Type 'tables' to list tables")
    click.echo("Type 'help' for help\n")

    while True:
        try:
            query = click.prompt("duckdb>", type=str)

            if query.lower() in ["exit", "quit"]:
                break
            elif query.lower() == "help":
                click.echo("\nCommands:")
                click.echo("  tables     - List all tables")
                click.echo("  describe <table> - Show table schema")
                click.echo("  exit/quit  - Exit interactive mode")
                click.echo("\nOr enter any SQL query\n")
                continue
            elif query.lower() == "tables":
                tables = ctx.obj["connection"].list_tables()
                for table in tables:
                    click.echo(f"  • {table}")
                continue
            elif query.lower().startswith("describe "):
                table_name = query.split(" ", 1)[1]
                ctx.invoke(describe, table_name=table_name)
                continue

            # Execute SQL query
            df = ctx.obj["query_engine"].execute_query(query)

            # Display results
            if len(df) > 0:
                click.echo(
                    tabulate(
                        df.head(50), headers="keys", tablefmt="grid", showindex=False
                    )
                )
                if len(df) > 50:
                    click.echo(f"\n... {len(df) - 50} more rows")
            else:
                click.echo("No results")

            click.echo(f"\n{len(df)} rows returned\n")

        except KeyboardInterrupt:
            click.echo("\nUse 'exit' or 'quit' to leave")
            continue
        except EOFError:
            break
        except Exception as e:
            click.echo(f"Error: {e}\n", err=True)

    click.echo("\nGoodbye!")


if __name__ == "__main__":
    main()
