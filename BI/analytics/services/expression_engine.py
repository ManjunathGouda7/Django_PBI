import re
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

class ExpressionEngine:
    """
    Dynamic Calculated Column & Formula Evaluation Engine.
    Safely computes derived mathematical & logical attributes on Pandas DataFrames.
    """

    ALLOWED_FUNCTIONS = {
        'abs': np.abs,
        'sqrt': np.sqrt,
        'log': np.log,
        'log10': np.log10,
        'exp': np.exp,
        'round': np.round,
        'ceil': np.ceil,
        'floor': np.floor
    }

    @classmethod
    def evaluate_expression(cls, df: pd.DataFrame, expression_str: str, new_col_name: str) -> Tuple[pd.DataFrame, str]:
        """
        Evaluates a formula string like '[Rectified Power [W]] / [Received Power [W]]' or '[PFO [mW]] * 1.5'
        and appends the new calculated column to the DataFrame.
        """
        if not expression_str or not expression_str.strip():
            raise ValueError("Expression string cannot be empty.")

        if not new_col_name or not new_col_name.strip():
            raise ValueError("New column name cannot be empty.")

        expr = expression_str.strip()
        new_col = new_col_name.strip()

        # Parse column references in square brackets [Column Name]
        col_refs = re.findall(r'\[(.*?)\]', expr)
        parsed_expr = expr

        # Map column references to df['col'] syntax
        for ref in set(col_refs):
            if ref not in df.columns:
                raise ValueError(f"Referenced column '{ref}' does not exist in dataset.")
            # Sanitize variable token
            safe_token = f"df['{ref}']"
            parsed_expr = parsed_expr.replace(f"[{ref}]", safe_token)

        # Build safe evaluation context
        eval_env = {'df': df, 'np': np, 'pd': pd}
        eval_env.update(cls.ALLOWED_FUNCTIONS)

        try:
            result_series = eval(parsed_expr, {"__builtins__": {}}, eval_env)
            if isinstance(result_series, (int, float, np.number)):
                df[new_col] = result_series
            elif isinstance(result_series, pd.Series):
                df[new_col] = result_series
            else:
                df[new_col] = pd.Series(result_series, index=df.index)
            
            return df, f"Successfully created calculated column '{new_col}'."
        except Exception as e:
            raise ValueError(f"Formula evaluation failed: {str(e)}")
