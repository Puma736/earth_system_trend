class DataSourceError(Exception):
    """Una fuente externa (POWER) falló o respondió algo inesperado."""


class DataNotAvailable(Exception):
    """Falta un dato local que hay que generar antes (por ejemplo, el CSV de FIRMS)."""
