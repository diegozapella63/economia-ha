# EconomIA 1.46.5: o teclado do celular não deixa a página em volta do app (a do Home Assistant) rolada. Ao abrir uma janela,
# o campo recebe o foco enquanto ela ainda sobe e o navegador rola as páginas em volta para mostrar o campo. Aqui o app fica
# dentro de um quadro, numa página rolada, e um campo de texto recebe o foco: a página de fora volta para o começo.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import App, check, pagina, resumo

QUADRO_TECLADO = """async (alvo) => {
  const f = document.createElement('iframe');
  f.src = location.href; f.style.cssText = 'display:block;width:320px;height:320px';
  const alto = document.createElement('div'); alto.style.height = '3000px';
  document.documentElement.style.cssText = 'height:auto;overflow:visible';
  document.body.style.cssText = 'height:auto;overflow:visible;display:block';
  document.body.append(f, alto);
  await new Promise((r) => (f.onload = r));
  await new Promise((r) => setTimeout(r, 400));
  window.scrollTo(0, 80);
  const antes = window.scrollY;
  const d = f.contentDocument, el = d.createElement(alvo);
  d.body.appendChild(el);
  el.dispatchEvent(new f.contentWindow.FocusEvent('focusin', { bubbles: true, composed: true }));
  await new Promise((r) => setTimeout(r, 200));
  const depois = window.scrollY;
  f.remove(); alto.remove();
  return [antes, depois];
}"""


async def main():
    async with async_playwright() as p:
        with App({}, buscar=False) as app:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            check(await pg.evaluate("window.__tecladoCalmo === true"), "o app liga a guarda do teclado")
            r = await pg.evaluate(QUADRO_TECLADO, "button")
            check(r == [80, 80], f"um botão não mexe na página de fora ({r})")
            r = await pg.evaluate(QUADRO_TECLADO, "textarea")
            check(r == [80, 0], f"um campo de texto põe a página de fora no começo ({r})")
            await b.close()


asyncio.run(main())
resumo()
