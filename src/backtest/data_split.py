"""División cronológica en período de entrenamiento (in-sample) y prueba
(out-of-sample). Nunca se mezcla al azar: en series de tiempo, mezclar filtraría
información del futuro hacia el pasado y arruinaría la prueba."""

import pandas as pd


def split_in_out_sample(df: pd.DataFrame, out_sample_frac: float = 0.3) -> tuple[pd.DataFrame, pd.DataFrame]:
    split_idx = int(len(df) * (1 - out_sample_frac))
    df_in = df.iloc[:split_idx].reset_index(drop=True)
    df_out = df.iloc[split_idx:].reset_index(drop=True)
    return df_in, df_out
