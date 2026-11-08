from playwright.async_api import Page
from .base import BaseScraper, Producto, registry, JS_TARJETAS, producto_desde_tarjeta


@registry.register("Unimarc")
class UnimarcScraper(BaseScraper):
    """Cada tarjeta muestra la promo ("4 x $3.000") antes del precio unitario ("$1.050 c/u")."""

    @property
    def nombre(self) -> str:
        return "Unimarc"

    def search_url(self, query: str) -> str:
        return f"https://www.unimarc.cl/search?q={query}"

    async def extraer(self, page: Page, query: str) -> list[Producto]:
        tarjetas = await page.evaluate(JS_TARJETAS, ["[class*=nameProduct]", "[class*=brandText]"])
        return [producto_desde_tarjeta(t, self.nombre) for t in tarjetas]
