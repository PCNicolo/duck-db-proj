# Bug Report

this .md file will be used to detail the bugs found when testing after implementing epic 1 with 7 stories

## Bug description:

Whenever a prompt is executed it gets hit with this ValueError: 
```t
ValueError: Invalid value of type 'builtins.str' received for the 'colorscale' property of heatmap
        Received value: 'default'

    The 'colorscale' property is a colorscale and may be
    specified as:
      - A list of colors that will be spaced evenly to create the colorscale.
        Many predefined colorscale lists are included in the sequential, diverging,
        and cyclical modules in the plotly.colors package.
      - A list of 2-element lists where the first element is the
        normalized color level value (starting at 0 and ending at 1),
        and the second item is a valid color string.
        (e.g. [[0, 'green'], [0.5, 'red'], [1.0, 'rgb(0, 0, 255)']])
      - One of the following named colorscales:
            ['aggrnyl', 'agsunset', 'algae', 'amp', 'armyrose', 'balance',
             'blackbody', 'bluered', 'blues', 'blugrn', 'bluyl', 'brbg',
             'brwnyl', 'bugn', 'bupu', 'burg', 'burgyl', 'cividis', 'curl',
             'darkmint', 'deep', 'delta', 'dense', 'earth', 'edge', 'electric',
             'emrld', 'fall', 'geyser', 'gnbu', 'gray', 'greens', 'greys',
             'haline', 'hot', 'hsv', 'ice', 'icefire', 'inferno', 'jet',
             'magenta', 'magma', 'matter', 'mint', 'mrybm', 'mygbm', 'oranges',
             'orrd', 'oryel', 'oxy', 'peach', 'phase', 'picnic', 'pinkyl',
             'piyg', 'plasma', 'plotly3', 'portland', 'prgn', 'pubu', 'pubugn',
             'puor', 'purd', 'purp', 'purples', 'purpor', 'rainbow', 'rdbu',
             'rdgy', 'rdpu', 'rdylbu', 'rdylgn', 'redor', 'reds', 'solar',
             'spectral', 'speed', 'sunset', 'sunsetdark', 'teal', 'tealgrn',
             'tealrose', 'tempo', 'temps', 'thermal', 'tropic', 'turbid',
             'turbo', 'twilight', 'viridis', 'ylgn', 'ylgnbu', 'ylorbr',
             'ylorrd'].
        Appending '_r' to a named colorscale reverses it.
```

```bash
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/streamlit/runtime/scriptrunner/exec_code.py", line 128, in exec_func_with_error_handling
    result = func()
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/streamlit/runtime/scriptrunner/script_runner.py", line 669, in code_to_exec
    exec(code, module.__dict__)  # noqa: S102
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/app.py", line 1826, in <module>
    main()
    ~~~~^^
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/app.py", line 176, in main
    visualizations_tab()
    ~~~~~~~~~~~~~~~~~~^^
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/app.py", line 1092, in visualizations_tab
    render_chart_creation(df)
    ~~~~~~~~~~~~~~~~~~~~~^^^^
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/app.py", line 1163, in render_chart_creation
    fig = create_heatmap(df, x_col, y_col, values_col, chart_config)
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/src/duckdb_analytics/visualizations/chart_types.py", line 34, in create_heatmap
    fig = go.Figure(data=go.Heatmap(
                         ~~~~~~~~~~^
        z=pivot_df.values,
        ^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
        showscale=True
        ^^^^^^^^^^^^^^
    ))
    ^
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/plotly/graph_objs/_heatmap.py", line 2461, in __init__
    self._set_property("colorscale", arg, colorscale)
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/plotly/basedatatypes.py", line 4403, in _set_property
    _set_property_provided_value(self, name, arg, provided)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/plotly/basedatatypes.py", line 398, in _set_property_provided_value
    obj[name] = val
    ~~~^^^^^^
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/plotly/basedatatypes.py", line 4932, in __setitem__
    self._set_prop(prop, value)
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/plotly/basedatatypes.py", line 5276, in _set_prop
    raise err
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/plotly/basedatatypes.py", line 5271, in _set_prop
    val = validator.validate_coerce(val)
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/_plotly_utils/basevalidators.py", line 1636, in validate_coerce
    self.raise_invalid_val(v)
    ~~~~~~~~~~~~~~~~~~~~~~^^^
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/_plotly_utils/basevalidators.py", line 298, in raise_invalid_val
            raise ValueError(
    ...<11 lines>...
            )
```


Heres another instance of the error, when i switched to the analytics tab and just hit execute template, it succeeds and displays the reuslts but also outputs this huge long error on the bottom

```bash
ValueError: Grouper for 'period' not 1-dimensional

File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/streamlit/runtime/scriptrunner/exec_code.py", line 128, in exec_func_with_error_handling
    result = func()
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/streamlit/runtime/scriptrunner/script_runner.py", line 669, in code_to_exec
    exec(code, module.__dict__)  # noqa: S102
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/app.py", line 1826, in <module>
    main()
    ~~~~^^
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/app.py", line 176, in main
    visualizations_tab()
    ~~~~~~~~~~~~~~~~~~^^
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/app.py", line 1092, in visualizations_tab
    render_chart_creation(df)
    ~~~~~~~~~~~~~~~~~~~~~^^^^
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/app.py", line 1163, in render_chart_creation
    fig = create_heatmap(df, x_col, y_col, values_col, chart_config)
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/src/duckdb_analytics/visualizations/chart_types.py", line 31, in create_heatmap
    pivot_df = df.pivot_table(index=y, columns=x, values=values,
                             aggfunc=config.get('aggregation', 'mean'))
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/pandas/core/frame.py", line 9516, in pivot_table
    return pivot_table(
        self,
    ...<9 lines>...
        sort=sort,
    )
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/pandas/core/reshape/pivot.py", line 102, in pivot_table
    table = __internal_pivot_table(
        data,
    ...<9 lines>...
        sort,
    )
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/pandas/core/reshape/pivot.py", line 172, in __internal_pivot_table
    grouped = data.groupby(keys, observed=observed_bool, sort=sort, dropna=dropna)
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/pandas/core/frame.py", line 9190, in groupby
    return DataFrameGroupBy(
        obj=self,
    ...<7 lines>...
        dropna=dropna,
    )
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/pandas/core/groupby/groupby.py", line 1330, in __init__
    grouper, exclusions, obj = get_grouper(
                               ~~~~~~~~~~~^
        obj,
        ^^^^
    ...<5 lines>...
        dropna=self.dropna,
        ^^^^^^^^^^^^^^^^^^^
    )
    ^
File "/Users/nicodiferdinando/Documents/Devolopment/duck-db-proj/.venv/lib/python3.13/site-packages/pandas/core/groupby/grouper.py", line 1038, in get_grouper
    raise ValueError(f"Grouper for '{name}' not 1-dimensional")

```


## Steps to reproduce:

when running the streamlit run app.py, this happens in the "Use Enhanced Editor (beta)" feature as well, so whenever i try to execute a query, it fails

## Expected vs actual behavior:

should just run the query and give me an output, the output is given but it still produces this large error

##S everity (Critical/High/Medium/Low):

Critical

## Which story/component it affects:

Any SQL exectuable query, inside of the analytics tab, and anytime anything is executed it seems, some variation of this error occurs
