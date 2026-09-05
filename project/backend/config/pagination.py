"""Shared pagination."""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """
    PageNumberPagination that honours ?page_size=.

    The stock class ignores the query parameter unless page_size_query_param is
    set, so a client asking for 200 rows silently received the default 50 --
    the payslip list showed 50 of 80 with no indication anything was missing.
    """

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500
