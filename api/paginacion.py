from rest_framework.pagination import PageNumberPagination


class PaginacionSGR(PageNumberPagination):
    """20 registros por página: ?page=2 pide la siguiente y ?page_size=50 cambia el tamaño (máximo 100)."""

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
