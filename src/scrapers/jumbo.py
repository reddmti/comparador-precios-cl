from playwright.async_api import Page
from .base import BaseScraper, Producto, registry, JS_TARJETAS, producto_desde_tarjeta


@registry.register("Jumbo")
class JumboScraper(BaseScraper):
    """Rediseño de jumbo.cl (sep-2026): el nombre va en un <h3> y la marca en el elemento anterior."""

    @property
    def nombre(self) -> str:
        return "Jumbo"

    def search_url(self, query: str) -> str:
        return f"https://www.jumbo.cl/busca/?ft={query}"

    async def extraer(self, page: Page, query: str) -> list[Producto]:
        tarjetas = await page.evaluate(JS_TARJETAS, ["h3.line-clamp-3", "p.text-gray-500"])
        return [producto_desde_tarjeta(t, self.nombre) for t in tarjetas]
