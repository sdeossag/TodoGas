"""
Paginacion por defecto de la API.

RF-AC-05 pide 50 resultados por pagina configurables a 100, y RNF-REN-01 fija
500 ms de respuesta. Sin un default global, cada endpoint nuevo nace devolviendo
la tabla entera: /api/assets/ enviaba los 3.940 activos en una sola respuesta.

El default va en REST_FRAMEWORK para que la regla aplique tambien a los
endpoints que aun no existen, no solo a los que hoy sabemos que pesan.
"""

from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
