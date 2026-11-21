// O teclado do celular: ao abrir uma janela, o campo recebe o foco enquanto ela ainda sobe, e o navegador rola as páginas
// em volta do app (a do Home Assistant) para "mostrar" o campo: a barra de cima some e a janela fica fora do lugar, até
// um toque. Aqui, quando um campo de texto recebe o foco (e quando o teclado muda a altura da tela), as páginas em volta
// voltam para o começo. A página do próprio app não é tocada. O mesmo código em todos os apps da família (teclado.js).
(function (win) {
  if (!win || win.__tecladoCalmo) return;
  win.__tecladoCalmo = true;
  const voltar = () => {
    for (const w of [win.parent, win.top]) {
      try {
        if (!w || w === win) continue;
        const el = w.document && w.document.scrollingElement;
        if (w.scrollY || (el && el.scrollTop)) w.scrollTo(0, 0);
      } catch (e) { /* outra origem: não dá para mexer */ }
    }
  };
  let ate = 0;
  const ciclo = () => { voltar(); if (Date.now() < ate) win.setTimeout(ciclo, 60); };
  win.addEventListener("focusin", (e) => {
    const t = (e.composedPath && e.composedPath()[0]) || e.target;
    if (!t || !/^(INPUT|TEXTAREA)$/.test(t.tagName || "")) return;
    const parado = Date.now() >= ate;
    ate = Date.now() + 900; // a janela sobe em 0,3 s e o teclado, logo depois
    if (parado) ciclo();
  }, true);
  if (win.visualViewport) win.visualViewport.addEventListener("resize", voltar);
})(window);
