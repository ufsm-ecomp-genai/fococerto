// Plugin PostCSS do tema laranja. Para cada regra com cor: reescreve a cor no tema claro (padrão) e cria a regra irmã
// `:root[data-theme="dark"] <seletor>` com a versão escura. Não toca no CSS do node_modules (Leaflet) nem em arquivos
// marcados com o comentário `tema: manual` (src/tema.css, escrito à mão para os dois temas).
import { valorClaro, valorEscuro, temCor } from './paleta.js';

const ESCURO = ':root[data-theme="dark"]';
const CROMO = /\.sidebar\b|\.page-overview\s*>\s*\.page-heading/;
const PROPS =
  /^(color|fill|stroke|caret-color|background(-color|-image)?|border(-(top|right|bottom|left))?(-color)?|outline(-color)?|box-shadow|text-decoration(-color)?|--[\w-]+)$/;

function partes(seletor) {
  const out = [];
  let nivel = 0,
    atual = '';
  for (const ch of seletor) {
    if (ch === '(' || ch === '[') nivel++;
    if (ch === ')' || ch === ']') nivel--;
    if (ch === ',' && !nivel) {
      out.push(atual);
      atual = '';
    } else atual += ch;
  }
  out.push(atual);
  return out.map((s) => s.trim()).filter(Boolean);
}
// variáveis (--border, --muted, --green): o papel vem do nome
const papelVariavel = (n) =>
  /border|line|divider/.test(n) ? 'border' : /bg|background|surface/.test(n) ? 'background' : 'color';
export function prefixar(seletor) {
  return partes(seletor)
    .map((s) => (/^(:root|html)\b/.test(s) ? s.replace(/^(:root|html)/, ESCURO) : `${ESCURO} ${s}`))
    .join(',');
}

export default function tema() {
  return {
    postcssPlugin: 'fococerto-tema',
    Once(root) {
      const arquivo = root.source?.input?.file || '';
      if (/node_modules/.test(arquivo)) return;
      let manual = false;
      root.walkComments((c) => {
        if (/tema:\s*manual/.test(c.text)) manual = true;
      });
      if (manual) return;
      root.walkRules((rule) => {
        if (rule.parent?.type === 'atrule' && /keyframes/.test(rule.parent.name)) return;
        if (rule.selector.includes('data-theme')) return;
        const cromo = CROMO.test(rule.selector),
          escuras = [];
        rule.each((decl) => {
          if (decl.type !== 'decl' || !PROPS.test(decl.prop) || !temCor(decl.value)) return;
          const prop = decl.prop.startsWith('--') ? papelVariavel(decl.prop) : decl.prop,
            claroV = valorClaro(decl.value, { prop, cromo });
          decl.value = claroV;
          const escuroV = valorEscuro(claroV, { prop, cromo });
          if (escuroV !== claroV) escuras.push(decl.clone({ value: escuroV }));
        });
        if (escuras.length) {
          const r = rule.clone({ selector: prefixar(rule.selector) });
          r.removeAll();
          escuras.forEach((d) => r.append(d));
          rule.after(r);
        }
      });
    },
  };
}
tema.postcss = true;
