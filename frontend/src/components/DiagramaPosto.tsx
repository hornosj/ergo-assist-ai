import { cm, type Medidas } from '../api'

// Vista lateral do posto ideal, em escala: os números do cálculo viram
// posição no desenho (assento, coxa, mesa, topo do monitor).
const ESCALA = 1.55 // px por cm
const CHAO = 290

const y = (alturaCm: number) => CHAO - alturaCm * ESCALA
const x = (cmHorizontal: number) => 70 + cmHorizontal * ESCALA

export default function DiagramaPosto({ m }: { m: Medidas }) {
  const assento = m.altura_assento_ideal_cm
  const profundidade = (m.profundidade_assento_ideal_cm[0] + m.profundidade_assento_ideal_cm[1]) / 2
  const coxa = m.comprimento_nadega_poplitea_cm
  const mesa = m.altura_mesa_ideal_cm
  const monitor = m.altura_topo_monitor_cm
  const olhos = assento + m.olhos_sentado_cm
  const ombro = assento + m.olhos_sentado_cm * 0.78
  const cotovelo = assento + m.cotovelo_sentado_cm

  const quadril = { x: x(4), y: y(assento) - 5 }
  const joelho = { x: x(4 + coxa), y: y(assento) - 5 }
  const pe = { x: joelho.x + 4, y: CHAO }
  const ombroP = { x: x(1), y: y(ombro) }
  const cotoveloP = { x: x(4), y: y(cotovelo) }
  const mao = { x: x(4 + 30), y: y(cotovelo) }
  const cabeca = { x: x(3), y: y(olhos) }

  return (
    <svg className="diagrama" viewBox="0 0 360 300" role="img" aria-label="Diagrama do posto ajustado">
      <line x1="10" x2="350" y1={CHAO} y2={CHAO} className="d-chao" />

      {/* cadeira */}
      <rect x={x(0)} y={y(assento)} width={profundidade * ESCALA} height="6" rx="3" className="d-cadeira" />
      <path d={`M ${x(0) + 2} ${y(assento)} L ${x(-4)} ${y(assento + 52)}`} className="d-cadeira-linha" />
      <line x1={x(profundidade / 2)} x2={x(profundidade / 2)} y1={y(assento) + 6} y2={CHAO - 10} className="d-cadeira-linha" />
      <line x1={x(profundidade / 2 - 18)} x2={x(profundidade / 2 + 18)} y1={CHAO - 8} y2={CHAO - 8} className="d-cadeira-linha" />

      {/* mesa e monitor */}
      <line x1={x(34)} x2="350" y1={y(mesa)} y2={y(mesa)} className="d-mesa" />
      <line x1="335" x2="335" y1={y(mesa)} y2={CHAO} className="d-mesa-perna" />
      <rect x={x(78)} y={y(monitor)} width="7" height={Math.max(20, (monitor - mesa - 10) * ESCALA)} rx="2" className="d-monitor" />
      <line x1={x(80)} x2={x(80)} y1={y(mesa)} y2={y(mesa) - 10} className="d-mesa-perna" />

      {/* pessoa */}
      <g className="d-pessoa">
        <circle cx={cabeca.x} cy={cabeca.y - 2} r="11" />
        <line x1={quadril.x} y1={quadril.y} x2={ombroP.x} y2={ombroP.y} />
        <line x1={ombroP.x} y1={ombroP.y} x2={cabeca.x} y2={cabeca.y + 9} />
        <line x1={quadril.x} y1={quadril.y} x2={joelho.x} y2={joelho.y} />
        <line x1={joelho.x} y1={joelho.y} x2={pe.x} y2={pe.y - 2} />
        <line x1={pe.x - 2} y1={pe.y - 2} x2={pe.x + 16} y2={pe.y - 2} />
        <line x1={ombroP.x} y1={ombroP.y} x2={cotoveloP.x} y2={cotoveloP.y} />
        <line x1={cotoveloP.x} y1={cotoveloP.y} x2={mao.x} y2={mao.y} />
      </g>
      <line x1={cabeca.x + 10} y1={y(olhos)} x2={x(78)} y2={y(olhos)} className="d-visao" />

      {/* cotas */}
      <Cota x={26} de={0} ate={assento} rotulo={cm(assento)} />
      <Cota x={348} de={0} ate={mesa} rotulo={cm(mesa)} lado="esq" />
      <text x={x(78) + 10} y={y(monitor) + 4} className="d-rotulo">topo da tela {cm(monitor)}</text>
      <text x={quadril.x + 6} y={joelho.y - 8} className="d-rotulo">coxa {cm(coxa)}</text>
    </svg>
  )
}

function Cota({ x: cx, de, ate, rotulo, lado = 'dir' }: { x: number; de: number; ate: number; rotulo: string; lado?: 'dir' | 'esq' }) {
  return (
    <g className="d-cota">
      <line x1={cx} x2={cx} y1={y(de)} y2={y(ate)} />
      <line x1={cx - 4} x2={cx + 4} y1={y(ate)} y2={y(ate)} />
      <text
        x={lado === 'dir' ? cx + 6 : cx - 6}
        y={(y(de) + y(ate)) / 2}
        textAnchor={lado === 'dir' ? 'start' : 'end'}
        className="d-rotulo"
      >
        {rotulo}
      </text>
    </g>
  )
}
