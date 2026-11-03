# EconomIA 0.19.0: o Roteiro: total, paradas da mais perto para a mais longe, pedido online do que sai mais barato com
# frete, o número de paradas (1 a 4) e a recomendação, Compare, "Sem limite de paradas", o que acaba (Acabando),
# preço de clube de quem é sócio, "Ainda sem preço" e o link da rota no Google Maps (com a casa no começo e no fim).
import asyncio
import urllib.parse
from datetime import datetime, timedelta, timezone

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, categoria, check, pagina, resumo

HOJE = (datetime.now(timezone.utc) - timedelta(hours=3)).date()
D = lambda n: (HOJE + timedelta(days=n)).isoformat()  # noqa: E731

OFERTAS = {"versao": 2, "gerado_em": "2026-11-02T10:00:00-03:00", "categorias": [
    categoria("mercados", [("merc-giassi", "Giassi", 0.8, {"endereco": "Rua A, 10"}), ("merc-bistek", "Bistek", 2.5),
                           ("merc-fort", "Fort Atacadista", 4.0, {"endereco": "Rua F, 400"})]),
    categoria("farmacias", [("farm-panvel", "Panvel", 1.2, {"endereco": "Rua P, 12"})]),
    categoria("online", [("onli-amazon", "Amazon", None)])],
    "lista": [{"produto": "Leite integral", "precos": {"merc-giassi": 4.89, "merc-bistek": 4.59, "merc-fort": 4.29}},
              {"produto": "Café Pilão 500 g", "precos": {"merc-giassi": 19.9, "merc-fort": 21.9, "onli-amazon": {"preco": 16.9, "frete": 0, "prazo_dias": 2}}},
              {"produto": "Arroz 5 kg", "precos": {"merc-giassi": 24.9, "merc-fort": 22.9}},
              {"produto": "Dipirona", "precos": {"farm-panvel": {"preco": 8.9, "clube": 7.9}}}]}


def antes(S):
    S.gravar_json(S.OFERTAS, OFERTAS)


async def total(pg):
    return (await pg.text_content("#rotRes .rot-total .por")).replace("\xa0", " ")


async def paradas(pg):
    return [(await li.locator(".parada-h b").inner_text()) for li in await pg.locator("#rotRes .parada").all()]


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados", "farmacias", "online"], "clubes": ["farm-panvel"],
           "lista": [{"produto": "Leite integral", "compras": [D(-14), D(-7)]}, {"produto": "Café Pilão 500 g"}, {"produto": "Arroz 5 kg"},
                     {"produto": "Dipirona"}, {"produto": "Abacaxi"}]}
    with App(cfg, buscar=False, antes=antes) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="roteiro"]')
            await pg.wait_for_timeout(400)
            check(await pg.text_content("#screenTitle") == "Roteiro", "tela do Roteiro")
            botoes = [t.strip() for t in await pg.locator("#rotParadas button").all_inner_texts()]
            check(botoes == ["1", "2", "3", "4"] and await pg.get_attribute('#rotParadas [data-v="2"]', "aria-pressed") == "true", "paradas de 1 a 4, 2 marcado")
            check(await pg.is_checked("#rotOnline"), "Pedir online ligado")
            # 2 paradas + o café online (mais barato com frete grátis)
            check(await total(pg) == "R$ 51,99", f"total do roteiro ({await total(pg)})")
            sub = (await pg.text_content("#rotRes .rot-sub")).replace("\xa0", " ")
            check("em 2 paradas + pedido online" in sub and "economia de R$ 3,97 sobre o preço médio" in sub, f"resumo do total ({sub})")
            check(await paradas(pg) == ["Panvel", "Fort Atacadista", "Amazon"], f"da loja mais perto para a mais longe, e o online no fim ({await paradas(pg)})")
            fort = (await pg.locator("#rotRes .parada", has_text="Fort").inner_text()).replace("\xa0", " ")
            check("Leite integral" in fort and "Arroz 5 kg" in fort and "Café" not in fort and "4,0 km" in fort, "o Fort leva leite e arroz")
            panvel = (await pg.locator("#rotRes .parada", has_text="Panvel").inner_text()).replace("\xa0", " ")
            check("R$ 7,90" in panvel and "CLUBE" in panvel.upper(), "Dipirona pelo preço de clube (é sócio)")
            amz = (await pg.locator("#rotRes .parada", has_text="Amazon").inner_text()).replace("\xa0", " ")
            check("Café Pilão 500 g" in amz and "chega em 2 dias" in amz, "o café pedido online, com o prazo")
            check("Ainda sem preço: Abacaxi." in await pg.text_content("#rotRes"), "o que ainda não tem preço")
            href = await pg.get_attribute('#rotRes a:has-text("Abrir rota no Maps")', "href")
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)
            check(q["origin"] == [CEP + ", Brasil"] and q["destination"] == [CEP + ", Brasil"], "a rota sai de casa e volta para casa")
            check(q["waypoints"] == [f"Panvel, Rua P, 12, {CEP}|Fort Atacadista, Rua F, 400, {CEP}"], f"as paradas na ordem, com o endereço ({q.get('waypoints')})")
            ops = [t.replace("\xa0", " ") for t in await pg.locator("#rotRes .rot-op").all_inner_texts()]
            check(len(ops) == 2 and "1 parada" in ops[0] and "sem 1 item" in ops[0] and "2 paradas · recomendado" in ops[1], f"Compare ({ops})")
            await pg.locator("#roteiro").screenshot(path=SHOTS + "/ecr-roteiro.png")
            # ver a opção de 1 parada no Compare
            await pg.click('#rotRes [data-rotk="1"]')
            check(await total(pg) == "R$ 44,09" and await paradas(pg) == ["Fort Atacadista", "Amazon"], "Compare: 1 parada no Fort")
            check("Sem preço nas lojas deste roteiro: Dipirona." in await pg.text_content("#rotRes"), "avisa o que fica de fora")
            # sem pedir online: tudo nas lojas
            await pg.click("#rotOnline")
            await pg.wait_for_timeout(700)
            check(app.config_salva()["roteiro"]["online"] is False, "Pedir online desligado fica salvo")
            check(await total(pg) == "R$ 56,99" and "Amazon" not in await paradas(pg), f"sem online: o café no Fort ({await total(pg)})")
            check("Sem limite de paradas: 3 lojas, R$ 54,99." in (await pg.text_content("#rotRes")).replace("\xa0", " "), "quanto daria sem limite de paradas")
            await pg.click('#rotParadas [data-v="3"]')
            await pg.wait_for_timeout(700)
            check(app.config_salva()["roteiro"]["paradas"] == 3, "3 paradas fica salvo")
            check(await total(pg) == "R$ 56,99", "com 3 paradas a economia é pouca: continua a recomendação de 2")
            nota = (await pg.text_content("#rotRes .i-nota")).replace("\xa0", " ")
            check("Com 3 paradas a economia sobe só R$ 2,00, por isso recomendo 2 paradas." in nota, f"explica a recomendação ({nota})")
            # só o que está acabando
            await pg.click('#rotEscopo [data-v="acabando"]')
            await pg.wait_for_timeout(700)
            check(app.config_salva()["roteiro"]["escopo"] == "acabando", "escopo salvo")
            check(await paradas(pg) == ["Fort Atacadista"] and await total(pg) == "R$ 4,29", "Acabando: só o leite, no Fort")
            await pg.locator("#roteiro").screenshot(path=SHOTS + "/ecr-acabando.png")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
