import {useEffect} from 'react';
import {MapContainer,TileLayer,CircleMarker,Marker,Polyline,Popup,useMap,useMapEvents} from 'react-leaflet';
import L from 'leaflet';
import {LocateFixed} from 'lucide-react';
const colors={oficial:'#28796b',osm:'#5d7d9e',estimada:'#ac8a42',declarada:'#8a61a0'};
function Controls({bbox,onClick,selected}) {
 const map=useMap();
 useEffect(()=>{if(bbox) map.fitBounds([[bbox[0],bbox[2]],[bbox[1],bbox[3]]],{padding:[24,24]});},[map,bbox]);
 useEffect(()=>{if(selected) map.flyTo([selected.lat,selected.lon],Math.max(map.getZoom(),9),{duration:.5});},[map,selected]);
 useEffect(()=>{const obs=new ResizeObserver(()=>map.invalidateSize());obs.observe(map.getContainer());return()=>obs.disconnect();},[map]);
 useMapEvents({click:e=>onClick?.(e.latlng)});
 return <button className="map-fit" title="Enquadrar região / Fit region" onClick={()=>bbox&&map.fitBounds([[bbox[0],bbox[2]],[bbox[1],bbox[3]]])}><LocateFixed size={18}/></button>;
}
export default function OperationMap({bbox,bases=[],occurrences=[],assignments=[],resources=[],onSelect,onClick,selected,t}) {
 return <MapContainer center={[0,0]} zoom={3} className="operation-map" scrollWheelZoom={false}>
  <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}" attribution="Tiles © Esri — Esri, HERE, Garmin, USGS, © OpenStreetMap contributors"/>
  <Controls bbox={bbox} onClick={onClick} selected={selected}/>
  {assignments.map((a,i)=>{const o=occurrences.find(x=>x.id===a.ocorrencia_id),r=resources.find(x=>x.id===a.recurso_id),b=bases.find(x=>x.id===r?.base_id);return o&&b?<Polyline key={i} positions={[[b.lat,b.lon],[o.lat,o.lon]]} pathOptions={{color:'#387b6b',weight:1.6,dashArray:'5 7',opacity:.65}}/>:null;})}
  {occurrences.map(o=><CircleMarker key={o.id} center={[o.lat,o.lon]} radius={selected?.id===o.id?11:6+o.prioridade*5} pathOptions={{color:'#fff',weight:2,fillColor:assignments.some(a=>a.ocorrencia_id===o.id)?'#e49b37':'#da684c',fillOpacity:.9}} eventHandlers={{click:()=>onSelect?.(o)}}><Popup><strong>{o.localidades?.[0]?.nome||o.id}</strong><p>{t('Prioridade')}: {o.prioridade?.toFixed(2)} · {o.n_focos} {t('focos')}</p>{t('até')} {o.pop_raio?.toLocaleString()} {t('habitantes no raio')}</Popup></CircleMarker>)}
  {bases.map(b=><Marker key={b.id} position={[b.lat,b.lon]} icon={L.divIcon({className:'base-marker',html:`<span style="background:${colors[b.confianca]||'#667b73'}"></span>`,iconSize:[14,14]})}><Popup><strong>{b.nome}</strong><p>{t(b.confianca||'Não disponível')} {b.simulada?`· ${t('Simulado')}`:''}</p>{b.confianca==='estimada'&&<p>{t('Sede municipal sem unidade verificada.')}</p>}<p>{b.fonte||t('Não disponível')}</p>{b.orgao&&<p>{b.orgao} · {b.data_fonte}</p>}{b.coordenada&&<p>{b.coordenada}</p>}</Popup></Marker>)}
 </MapContainer>;
}
