from playwright.async_api import Page
from .base import BaseScraper, Producto, registry, JS_TARJETAS, producto_desde_tarjeta


@registry.register("Santa Isabel")
class SantaIsabelScraper(BaseScraper):
    """Plataforma Cencosud, igual que Jumbo, pero aún conserva .product-card-name (sep-2026)."""

    @property
    def nombre(self) -> str:
        return "Santa Isabel"

    def search_url(self, query: str) -> str:
        return f"https://www.santaisabel.cl/busca/?ft={query}"

    async def extraer(self, page: Page, query: str) -> list[Producto]:
        tarjetas = await page.evaluate(JS_TARJETAS, [".product-card-name", None])
        return [producto_desde_tarjeta(t, self.nombre) for t in tarjetas]
