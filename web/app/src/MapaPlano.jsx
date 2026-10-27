import { useEffect, Fragment } from 'react';
import { MapContainer, TileLayer, CircleMarker, Marker, Polyline, Popup, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { LocateFixed } from 'lucide-react';
import { CORES, ESTILO_BASE, faixas, procedencia, escalados, fmt, fmtPrio } from './lib.js';
function Controls({ bbox, onClick, selected }) {
  const map = useMap();
  useEffect(() => {
    if (!bbox) return;
    // enquadra de novo quando o mapa ganha o tamanho final (o layout da página termina depois da montagem)
    const enquadrar = () => {
      map.invalidateSize();
      map.fitBounds(
        [
          [bbox[0], bbox[2]],
          [bbox[1], bbox[3]],
        ],
        { padding: [24, 24] },
      );
    };
    enquadrar();
    const timer = setTimeout(enquadrar, 250);
    return () => clearTimeout(timer);
  }, [map, bbox]);
  useEffect(() => {
    if (selected) map.flyTo([selected.lat, selected.lon], Math.max(map.getZoom(), 9), { duration: 0.5 });
  }, [map, selected]);
  useEffect(() => {
    const obs = new ResizeObserver(() => map.invalidateSize());
    obs.observe(map.getContainer());
    return () => obs.disconnect();
  }, [map]);
  useMapEvents({ click: (e) => onClick?.(e.latlng) });
  return (
    <button
      className="map-fit"
      title="Enquadrar região / Fit region"
      onClick={() =>
        bbox &&
        map.fitBounds([
          [bbox[0], bbox[2]],
          [bbox[1], bbox[3]],
        ])
      }
    >
      <LocateFixed size={18} />
    </button>
  );
}
const baseIcon = (p, n) =>
  L.divIcon({
    className: 'base-marker',
    html: `<span style="background:${ESTILO_BASE[p]?.cor || '#667b73'};border-style:${ESTILO_BASE[p]?.borda || 'solid'}"></span>${n ? `<b>${n}</b>` : ''}`,
    iconSize: [14, 14],
  });
export default function OperationMap({
  bbox,
  bases = [],
  occurrences = [],
  assignments = [],
  resources = [],
  escalations = [],
  onSelect,
  onClick,
  selected,
  crewCounts,
  locale,
  t,
}) {
  const faixa = faixas(occurrences),
    esc = escalados(escalations);
  return (
    <MapContainer center={[0, 0]} zoom={3} className="operation-map" scrollWheelZoom={false}>
      <TileLayer
        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
        attribution="Tiles © Esri — Esri, HERE, Garmin, USGS, © OpenStreetMap contributors"
      />
      <Controls bbox={bbox} onClick={onClick} selected={selected} />
      {assignments.map((a, i) => {
        const o = occurrences.find((x) => x.id === a.ocorrencia_id),
          r = resources.find((x) => x.id === a.recurso_id),
          b = bases.find((x) => x.id === r?.base_id);
        return o && b ? (
          <Polyline
            key={i}
            positions={[
              [b.lat, b.lon],
              [o.lat, o.lon],
            ]}
            pathOptions={{
              color: '#1565c0',
              weight: 3,
              opacity: 0.8,
              dashArray: r.tipo === 'aereo' ? '2 6' : undefined,
            }}
          >
            <Popup>
              <strong>
                {a.ordem}. {a.recurso_id} → {o.localidades?.[0]?.nome || o.id}
              </strong>
              <p>
                ETA ~{fmt(a.eta_h, locale)} h ({t('estimativa')})
              </p>
              <p>{a.justificativa}</p>
            </Popup>
          </Polyline>
        ) : null;
      })}
      {occurrences.map((o) => {
        const r = selected?.id === o.id ? 11 : 5 + Math.sqrt(o.n_focos || 1) * 2,
          e = esc[o.id];
        return (
          <Fragment key={o.id}>
            {e && (
              <CircleMarker
                center={[o.lat, o.lon]}
                radius={r + 6}
                interactive={false}
                pathOptions={{ color: '#000', weight: 3, dashArray: '4 4', fill: false }}
              />
            )}
            <CircleMarker
              center={[o.lat, o.lon]}
              radius={r}
              pathOptions={{ color: '#333', weight: 1, fillColor: CORES[faixa[o.id]], fillOpacity: 0.85 }}
              eventHandlers={{ click: () => onSelect?.(o) }}
            >
              <Popup>
                <strong>{o.localidades?.[0]?.nome || o.id}</strong>
                <p>
                  {t('Prioridade')}: {fmtPrio(o.prioridade, locale)} ({t('faixa')} {t(faixa[o.id])}) · {o.n_focos}{' '}
                  {t('focos')}
                </p>
                <p>
                  {t('até')} {fmt(o.pop_raio, locale, 0)} {t('habitantes no raio')}
                </p>
                {e && (
                  <p className="popup-esc">
                    {t('Escalada')}: {t('decisão humana necessária')}
                  </p>
                )}
              </Popup>
            </CircleMarker>
          </Fragment>
        );
      })}
      {bases.map((b) => {
        const p = procedencia(b),
          crews = resources.filter((r) => r.base_id === b.id);
        return (
          <Marker key={b.id} position={[b.lat, b.lon]} icon={baseIcon(p, crewCounts ? crews.length : 0)}>
            <Popup>
              <strong>{b.nome}</strong>
              <p>
                {t(p)} {b.simulada ? `· ${t('Simulado')}` : ''}
              </p>
              {p === 'estimada' && <p>{t('Sede municipal sem unidade verificada.')}</p>}
              <p>{b.fonte || t('Não disponível')}</p>
              {b.orgao && (
                <p>
                  {b.orgao} · {b.data_fonte}
                </p>
              )}
              {b.coordenada && <p>{b.coordenada}</p>}
              {crews.length > 0 && (
                <p>
                  <b>{t('Equipes')}:</b> {crews.map((r) => `${r.id} (${t(r.tipo)})`).join(', ')}
                </p>
              )}
            </Popup>
          </Marker>
        );
      })}
    </MapContainer>
  );
}
