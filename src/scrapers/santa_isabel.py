from playwright.async_api import Page
from .base import BaseScraper, Producto, registry, JS_TARJETAS, producto_desde_tarjeta


@registry.register("Santa Isabel")
class SantaIsabelScraper(BaseScraper):
    """
    Plataforma Cencosud, igual que Jumbo.

    Hasta oct-2026 conservaba `.product-card-name`; en nov-2026 adoptó el rediseño que
    Jumbo estrenó en sep-2026, con los mismos selectores. La clase quedó separada de la
    de Jumbo porque solo comparten la plataforma, no el calendario de despliegue.
    """

    @property
    def nombre(self) -> str:
        return "Santa Isabel"

    def search_url(self, query: str) -> str:
        return f"https://www.santaisabel.cl/busca/?ft={query}"

    async def extraer(self, page: Page, query: str) -> list[Producto]:
        tarjetas = await page.evaluate(JS_TARJETAS, ["h3.line-clamp-3", "p.text-gray-500"])
        return [producto_desde_tarjeta(t, self.nombre) for t in tarjetas]
