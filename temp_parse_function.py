def _parse_detailed_response(self, response: str) -> Tuple[str, str]:
    """Parse detailed mode response to extract SQL and thinking process."""
    try:
        logger.info(f"Parsing detailed response (first 200 chars): {response[:200]}...")
        
        # Look for SQL section in multiple ways
        sql_markers = ["SQL:", "```sql", "**SQL:**", "SELECT", "WITH", "INSERT", "UPDATE", "DELETE"]
        sql_start = -1
        
        for marker in sql_markers:
            pos = response.find(marker)
            if pos != -1:
                sql_start = pos
                break
        
        if sql_start != -1:
            # Extract thinking process (everything before SQL)
            thinking_process = response[:sql_start].strip()
            
            # Extract SQL query
            sql_part = response[sql_start:]
            
            # Clean up SQL part based on what we found
            if "```sql" in sql_part:
                sql_start_code = sql_part.find("```sql") + 6
                sql_end_code = sql_part.find("```", sql_start_code)
                if sql_end_code != -1:
                    sql_query = sql_part[sql_start_code:sql_end_code].strip()
                else:
                    sql_query = sql_part[sql_start_code:].strip()
            elif "SQL:" in sql_part:
                sql_query = sql_part.replace("SQL:", "").strip()
            else:
                # Just take everything after the marker
                sql_query = sql_part.strip()
            
            # Clean the extracted SQL
            sql_query = self._clean_sql_output(sql_query)
            
            logger.info(f"Extracted thinking process length: {len(thinking_process)}")
            logger.info(f"Extracted SQL: {sql_query}")
            
            # If we didn't get much thinking process, use the whole response as thinking
            if len(thinking_process.strip()) < 100:
                logger.warning("Short thinking process, using full response as thinking")
                thinking_process = response
            
            return sql_query, thinking_process
        else:
            # No clear SQL marker found - check for detailed response markers
            detailed_markers = ["🎯 STRATEGY:", "📊 BUSINESS CONTEXT:", "🔍 SCHEMA DECISIONS:", "✅ IMPLEMENTATION:"]
            marker_count = sum(1 for marker in detailed_markers if marker in response)
            
            if marker_count >= 2:
                # This looks like a detailed response, try to extract SQL from lines
                logger.info(f"Found {marker_count} detailed markers, treating as structured response")
                lines = response.split('\n')
                sql_lines = []
                found_sql = False
                
                for line in lines:
                    if line.strip().upper().startswith(('SELECT', 'WITH', 'INSERT', 'UPDATE', 'DELETE')):
                        found_sql = True
                    if found_sql:
                        sql_lines.append(line)
                
                if sql_lines:
                    sql_query = '\n'.join(sql_lines)
                    sql_query = self._clean_sql_output(sql_query)
                    thinking_process = response.replace('\n'.join(sql_lines), '').strip()
                    return sql_query, thinking_process
                else:
                    # No SQL found in detailed response, use whole response as thinking
                    return "SELECT 1;", response
            else:
                # Not a detailed response
                if len(response.strip()) > 100:
                    return self._clean_sql_output(response), response
                else:
                    return self._clean_sql_output(response), "Quick SQL generation without detailed analysis"
            
    except Exception as e:
        logger.warning(f"Failed to parse detailed response: {e}")
        return self._clean_sql_output(response), f"Response parsing failed: {response[:200]}..."