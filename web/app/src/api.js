export class ApiError extends Error {
  constructor(detail, status) {
    super(Array.isArray(detail) ? detail.map(e => `${e.loc?.slice(1).join(' → ')}: ${e.msg}`).join('\n') : String(detail));
    this.details = Array.isArray(detail) ? detail : [];
    this.status = status;
  }
}
export async function api(path, body, signal) {
  const response = await fetch(path, {signal, ...(body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})});
  const data = await response.json();
  if (!response.ok) throw new ApiError(data.detail || response.statusText, response.status);
  return data;
}
export const enc = encodeURIComponent;
export function scenarioPayload(scenario, region, period) { return {...scenario,regiao:region,periodo:period,reserva:Number(scenario.reserva),recursos:scenario.recursos.map(r=>({...r,capacidade:Number(r.capacidade)}))}; }
export function resourceErrors(error,index) { return error?.details?.filter(e=>e.loc?.includes('recursos') && e.loc[e.loc.indexOf('recursos')+1]===index).map(e=>e.msg) || []; }
