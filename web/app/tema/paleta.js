// Paleta laranja (clara e escura) a partir das cores fixas da v1. Funções puras, usadas pelo plugin PostCSS
// (tema/postcss-tema.js) no dev e no build: os arquivos de CSS da v1 não mudam no disco.
//
// Papel de cada cor = propriedade CSS + seletor:
// - "cromo": barra lateral e cabeçalho da visão geral (eram verde-escuro) -> grafite quente
// - fundo saturado fora do cromo (botão primário, passo atual, barras) -> laranja de destaque
// - o resto dos verdes -> mesmo tom laranja, mantendo a claridade (creme, pêssego, cinza quente)
// O tema escuro remapeia a claridade de TODAS as cores conforme o papel (fundo, texto, borda).

export const TOM = 24; // laranja (graus)
export const DESTAQUE = { h: TOM, s: 0.78, l: 0.4 }; // ~#b5501a: texto branco com contraste >= 4,5:1
const GRAFITE_S = 0.1;

export function parse(hex) {
  let h = hex.replace('#', '');
  if (h.length === 3 || h.length === 4) h = [...h].map((c) => c + c).join('');
  const a = h.length === 8 ? h.slice(6) : '';
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
  const max = Math.max(r, g, b),
    min = Math.min(r, g, b),
    l = (max + min) / 2,
    d = max - min;
  let H = 0,
    s = 0;
  if (d) {
    s = d / (1 - Math.abs(2 * l - 1));
    H = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
    H *= 60;
    if (H < 0) H += 360;
  }
  return { h: H, s: Math.min(1, s), l, a };
}
export function format({ h, s, l, a = '' }) {
  s = Math.max(0, Math.min(1, s));
  l = Math.max(0, Math.min(1, l));
  const c = (1 - Math.abs(2 * l - 1)) * s,
    x = c * (1 - Math.abs(((h / 60) % 2) - 1)),
    m = l - c / 2;
  const [r, g, b] =
    h < 60
      ? [c, x, 0]
      : h < 120
        ? [x, c, 0]
        : h < 180
          ? [0, c, x]
          : h < 240
            ? [0, x, c]
            : h < 300
              ? [x, 0, c]
              : [c, 0, x];
  return (
    '#' +
    [r, g, b]
      .map((v) =>
        Math.round((v + m) * 255)
          .toString(16)
          .padStart(2, '0'),
      )
      .join('') +
    a
  );
}
export const ehVerde = (c) => c.s > 0.08 && c.h >= 70 && c.h <= 180;
const ehFundo = (p) => /^background/.test(p);
const ehTexto = (p) => p === 'color' || p === 'fill' || p === 'caret-color';

export function claro(hex, { prop = '', cromo = false } = {}) {
  const c = parse(hex);
  // texto acinzentado fora do cromo (verde ou não): tom quente e escuro o bastante para 4,5:1 sobre fundo claro
  if (!cromo && ehTexto(prop) && c.s < 0.25 && c.l >= 0.35 && c.l < 0.72)
    return format({ h: TOM, s: Math.min(c.s, 0.1), l: Math.min(c.l, 0.42), a: c.a });
  if (!ehVerde(c)) return hex;
  if (cromo && c.l < 0.5) return format({ h: TOM, s: GRAFITE_S, l: c.l * 0.85, a: c.a }); // grafite quente
  if (cromo) return format({ h: TOM, s: Math.min(c.s, 0.35), l: c.l, a: c.a }); // texto claro do cromo
  if ((ehFundo(prop) || /^border/.test(prop)) && c.s > 0.3 && c.l < 0.62)
    return format({ ...DESTAQUE, l: Math.min(0.42, 0.39 + (c.l - 0.2) * 0.2), a: c.a }); // botão, passo atual, barra
  if (ehTexto(prop) && c.s > 0.2 && c.l < 0.6)
    return format({ h: TOM, s: Math.min(0.75, c.s + 0.15), l: Math.min(c.l, 0.4), a: c.a }); // texto laranja legível
  if (c.l < 0.3) return format({ h: TOM, s: Math.min(c.s, 0.15), l: c.l, a: c.a }); // texto escuro -> grafite
  return format({ h: TOM + 6, s: Math.min(c.s * 1.15, 0.7), l: c.l, a: c.a }); // tintas claras -> creme/pêssego
}

// recebe a cor JÁ no tema claro (ou uma cor que não era verde) e devolve a do tema escuro
export function escuro(hex, { prop = '', cromo = false } = {}) {
  const c = parse(hex),
    destaque = c.s > 0.5 && c.l >= 0.35 && c.l <= 0.65;
  // tintas de status (vermelho, azul, amarelo...) guardam o tom; creme/pêssego/cinza quente viram preto neutro
  const quente = c.h >= 15 && c.h <= 50,
    status = c.s > 0.3 && !quente;
  if (cromo) {
    if (ehTexto(prop) || c.l >= 0.5) return ehTexto(prop) && c.s < 0.3 ? format({ ...c, s: Math.min(c.s, 0.04) }) : hex;
    return format({ h: 0, s: 0, l: Math.min(c.l * 0.5, 0.06), a: c.a }); // barra lateral e cabeçalho: quase preto
  }
  if (ehFundo(prop)) {
    if (destaque) return format({ ...c, l: Math.min(0.62, c.l + 0.14) }); // laranja mais vivo (texto escuro, tema.css)
    if (c.l >= 0.6 && status) return format({ h: c.h, s: Math.min(c.s, 0.3), l: 0.09 + (1 - c.l) * 0.25, a: c.a }); // tinta de status escurecida
    if (c.l >= 0.6) return format({ h: 0, s: 0, l: Math.max(0.04, 0.1 - (1 - c.l) * 0.6), a: c.a }); // superfícies: cards #1a1a1a, página ~#131313
    return hex;
  }
  if (ehTexto(prop)) {
    if (c.l >= 0.7) return c.s < 0.3 ? format({ ...c, s: Math.min(c.s, 0.04) }) : hex; // texto claro continua
    if (c.s > 0.35) return format({ ...c, l: Math.max(0.64, 1 - c.l) }); // texto colorido
    return format({ h: c.h, s: Math.min(c.s, 0.04), l: Math.min(0.93, Math.max(0.7, 1 - c.l * 0.9)) }); // texto neutro
  }
  if (/^(border|outline)/.test(prop) && c.l >= 0.6)
    return format({ h: c.h, s: status ? Math.min(c.s, 0.2) : 0, l: 0.2, a: c.a });
  if (prop === 'box-shadow' && c.a) return format({ h: 0, s: 0, l: 0, a: c.a }); // sombra com transparência
  return hex;
}

const HEX = /#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3,4}\b/g;
const PALAVRA = /(^|[\s,(])(white|black)(?=$|[\s,)!;])/g;
const nomes = { white: '#ffffff', black: '#000000' };
export function valorClaro(valor, opts) {
  return valor.replace(HEX, (h) => claro(h, opts));
}
export function valorEscuro(valor, opts) {
  return valor.replace(PALAVRA, (m, p, n) => p + nomes[n]).replace(HEX, (h) => escuro(h, opts));
}
export const temCor = (valor) => {
  HEX.lastIndex = 0;
  PALAVRA.lastIndex = 0;
  const r = HEX.test(valor) || PALAVRA.test(valor);
  HEX.lastIndex = 0;
  PALAVRA.lastIndex = 0;
  return r;
};
