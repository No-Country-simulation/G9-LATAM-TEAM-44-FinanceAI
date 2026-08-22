/* FinanceAI · frontend
 *
 * JavaScript plano, sin dependencias ni empaquetador. Los gráficos son SVG
 * hecho a mano; una librería de charts habría pesado más que la app entera.
 *
 * Solo habla con el backend Java (:8080). El ml-service no se expone al
 * navegador.
 */
'use strict';

// --------------------------------------------------------------- constantes

const CATEGORIAS = [
  'alimentacion', 'transporte', 'salud', 'vivienda',
  'educacion', 'ocio', 'servicios', 'otras',
];

const MONEDAS = {
  ARS: { locale: 'es-AR', simbolo: '$' },
  BOB: { locale: 'es-BO', simbolo: 'Bs.' },
  BRL: { locale: 'pt-BR', simbolo: 'R$' },
  CLP: { locale: 'es-CL', simbolo: '$' },
  COP: { locale: 'es-CO', simbolo: '$' },
  CRC: { locale: 'es-CR', simbolo: '₡' },
  DOP: { locale: 'es-DO', simbolo: 'RD$' },
  GTQ: { locale: 'es-GT', simbolo: 'Q' },
  HNL: { locale: 'es-HN', simbolo: 'L' },
  MXN: { locale: 'es-MX', simbolo: '$' },
  NIO: { locale: 'es-NI', simbolo: 'C$' },
  PAB: { locale: 'es-PA', simbolo: 'B/.' },
  PEN: { locale: 'es-PE', simbolo: 'S/' },
  PYG: { locale: 'es-PY', simbolo: '₲' },
  USD: { locale: 'en-US', simbolo: '$' },
  UYU: { locale: 'es-UY', simbolo: '$U' },
  VES: { locale: 'es-VE', simbolo: 'Bs.' },
};

/* El valor canónico va sin tildes (es el que usan la API y el modelo). Aquí se
   traduce para pantalla. */
const NOMBRE_CATEGORIA = {
  alimentacion: 'Alimentación',
  transporte: 'Transporte',
  salud: 'Salud',
  vivienda: 'Vivienda',
  educacion: 'Educación',
  ocio: 'Ocio',
  servicios: 'Servicios',
  otras: 'Otros gastos',
};

/**
 * Devuelve la referencia a la variable CSS, no el color resuelto.
 *
 * Con getComputedStyle el color queda congelado al dibujar y los gráficos ya
 * pintados no siguen el cambio de tema. Dejando `var(--c-x)` en el SVG, el
 * navegador lo reevalúa solo.
 */
function colorCategoria(categoria) {
  return CATEGORIAS.includes(categoria) ? `var(--c-${categoria})` : 'var(--c-otras)';
}

const COLOR_PERFIL = {
  'Saludable': 'var(--verde)',
  'En observación': 'var(--ambar)',
  'En riesgo': 'var(--rojo)',
};

const CLASE_PERFIL = {
  'Saludable': 'saludable',
  'En observación': 'observacion',
  'En riesgo': 'riesgo',
};

const RESUMEN_PERFIL = {
  'Saludable': 'Tus indicadores están en rango. El objetivo ahora es sostener el hábito.',
  'En observación': 'Todavía no es crítico, pero el margen se está estrechando.',
  'En riesgo': 'Hay señales que conviene atender este mes, no el próximo.',
};

const NOMBRE_FACTOR = {
  tasa_gasto: 'Proporción del ingreso que gastas',
  ratio_endeudamiento: 'Nivel de endeudamiento',
  relacion_deuda_ingreso: 'Relación deuda / ingreso',
  capacidad_ahorro: 'Capacidad de ahorro',
  ahorro_ordinal: 'Hábito de ahorro',
  frecuencia_ahorro: 'Frecuencia de ahorro',
  gasto_total: 'Gasto total del periodo',
  ingreso_mensual: 'Ingreso mensual',
  gasto_esencial_pct: 'Peso de los gastos esenciales',
  gasto_discrecional_pct: 'Peso de los gastos prescindibles',
  concentracion_gasto: 'Concentración del gasto',
  categorias_activas: 'Categorías con gasto',
  vivienda_sobre_ingreso: 'Vivienda sobre el ingreso',
  carga_deuda_absoluta: 'Deuda en valor absoluto',
  pct_alimentacion: 'Peso de alimentación',
  pct_transporte: 'Peso de transporte',
  pct_salud: 'Peso de salud',
  pct_vivienda: 'Peso de vivienda',
  pct_educacion: 'Peso de educación',
  pct_ocio: 'Peso de ocio',
  pct_servicios: 'Peso de servicios',
  pct_otras: 'Peso de otros gastos',
};

const EJEMPLOS = {
  saludable: {
    ingreso: 4500, deuda: 12, ahorro: 'Alta',
    transacciones: [
      ['Supermercado Exito', 420], ['Gasolinera Terpel', 180],
      ['Netflix Streaming', 40], ['Arriendo Apartamento', 900],
    ],
  },
  observacion: {
    ingreso: 3000, deuda: 35, ahorro: 'Media',
    transacciones: [
      ['TRF/POS Supermercado Jumbo REF993021', 620], ['Uber Trip BOGOTA', 240],
      ['Cinepolis Entradas', 180], ['Arriendo Apartamento', 1100],
      ['Farmacia San Pablo', 130],
    ],
  },
  riesgo: {
    ingreso: 2200, deuda: 65, ahorro: 'Nula',
    transacciones: [
      ['### supermercado ara', 700], ['Bar El Callejon', 380],
      ['Steam Games', 210], ['Cuota Hipoteca Vivienda', 1200],
      ['Gasolinera Pemx', 260],
    ],
  },
};

const CLAVE_HISTORIAL = 'financeai.historial';
const CLAVE_TEMA = 'financeai.tema';

/* Estrategia de abstención (Fase 12): estado explícito que ya calcula
   srv-python/srv-java a partir de la confianza de cada transacción. */
const NOMBRE_ESTADO_CONFIANZA = {
  aceptado: 'Aceptado',
  requiere_revision: 'Requiere revisión',
  otras: 'Confianza insuficiente',
};

const CLASE_ESTADO_CONFIANZA = {
  aceptado: 'estado-aceptado',
  requiere_revision: 'estado-revision',
  otras: 'estado-insuficiente',
};

/* Umbrales por defecto de la estrategia de abstención (srv-python/app/modelos.py:
   umbral_confianza=0.5, umbral_confianza_alta=0.8). No vienen en
   /metricas-modelo, así que se documentan aquí para dibujar las líneas de
   referencia de la curva de cobertura. */
const UMBRAL_REQUIERE_REVISION = 0.5;
const UMBRAL_ACEPTADO = 0.8;

// ------------------------------------------------------------------ helpers

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

const dinero = new Intl.NumberFormat('es', { maximumFractionDigits: 0 });
const decimal = new Intl.NumberFormat('es', { maximumFractionDigits: 2 });

function monedaSeleccionada() {
  return $('#moneda')?.value || 'COP';
}

function dineroMoneda(valor, moneda = monedaSeleccionada()) {
  const configuracion = MONEDAS[moneda] || MONEDAS.COP;
  return new Intl.NumberFormat(configuracion.locale, {
    style: 'currency', currency: moneda, currencyDisplay: 'symbol', maximumFractionDigits: 2,
  }).format(valor);
}

function actualizarSimboloMoneda() {
  const configuracion = MONEDAS[monedaSeleccionada()] || MONEDAS.COP;
  $('#simbolo-moneda').textContent = configuracion.simbolo;
}

function leerMonto(valor) {
  const texto = String(valor ?? '').trim().replace(/[^\d,.-]/g, '');
  if (!texto) return NaN;

  const ultimoPunto = texto.lastIndexOf('.');
  const ultimaComa = texto.lastIndexOf(',');
  const separadorDecimal = ultimoPunto > ultimaComa ? '.' : ',';
  const tieneAmbos = ultimoPunto >= 0 && ultimaComa >= 0;
  const partes = texto.split(separadorDecimal);
  const ultimaParte = partes.at(-1) || '';
  const pareceDecimal = !tieneAmbos && ultimaParte.length > 0 && ultimaParte.length <= 2;

  if (tieneAmbos || pareceDecimal) {
    const entero = partes.slice(0, -1).join('').replace(/\D/g, '');
    const decimal = ultimaParte.replace(/\D/g, '');
    return Number(`${entero || '0'}.${decimal}`);
  }

  return Number(texto.replace(/\D/g, ''));
}

function formatearMonto(valor, moneda = monedaSeleccionada()) {
  if (!Number.isFinite(valor)) return '';
  const configuracion = MONEDAS[moneda] || MONEDAS.COP;
  return new Intl.NumberFormat(configuracion.locale, {
    maximumFractionDigits: 2,
  }).format(valor);
}

function actualizarCampoIngreso(formatear = true) {
  const campo = $('#ingreso');
  const valor = leerMonto(campo.value);
  campo.value = formatear ? formatearMonto(valor) : (Number.isFinite(valor) ? String(valor) : '');
}

const sinMovimiento = () =>
  typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

function crear(etiqueta, props = {}, hijos = []) {
  const nodo = document.createElement(etiqueta);
  for (const [clave, valor] of Object.entries(props)) {
    if (clave === 'class') nodo.className = valor;
    else if (clave === 'text') nodo.textContent = valor;
    else if (clave === 'html') nodo.innerHTML = valor;
    else nodo.setAttribute(clave, valor);
  }
  for (const hijo of hijos) nodo.append(hijo);
  return nodo;
}

function svg(etiqueta, atributos = {}) {
  const nodo = document.createElementNS('http://www.w3.org/2000/svg', etiqueta);
  for (const [clave, valor] of Object.entries(atributos)) nodo.setAttribute(clave, valor);
  return nodo;
}

/** Icono del sprite en línea. */
function icono(nombre, clase = 'ic') {
  const lienzo = svg('svg', { class: clase });
  const uso = svg('use');
  uso.setAttribute('href', `#i-${nombre}`);
  lienzo.append(uso);
  return lienzo;
}

/** Cuenta desde 0 hasta el valor final con salida cúbica. */
function animarNumero(nodo, hasta, formatear, duracion = 900) {
  if (sinMovimiento() || !Number.isFinite(hasta)) {
    nodo.textContent = formatear(hasta || 0);
    return;
  }
  const inicio = performance.now();
  const paso = (ahora) => {
    const t = Math.min(1, (ahora - inicio) / duracion);
    const suave = 1 - Math.pow(1 - t, 3);
    nodo.textContent = formatear(hasta * suave);
    if (t < 1) requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
}

function tostada(mensaje) {
  const nodo = crear('div', { class: 'tostada' }, [icono('alerta'), crear('span', { text: mensaje })]);
  $('#tostadas').append(nodo);
  setTimeout(() => {
    nodo.classList.add('saliendo');
    setTimeout(() => nodo.remove(), 320);
  }, 5200);
}

// ---------------------------------------------------------------------- API

/**
 * Resuelve la URL del backend probando primero el mismo origen.
 *
 * Detrás de nginx el backend cuelga de /api/v1 del mismo host y no hay CORS;
 * abriendo el HTML suelto hay que ir a localhost:8080. Se prueba en vez de
 * configurarlo para no depender de una variable.
 */
const Api = {
  base: null,

  /** Candidatas en orden: mismo origen, y el puerto 8080 del mismo host. */
  candidatas() {
    const protocolo = location.protocol === 'https:' ? 'https:' : 'http:';
    // Sin hostname (al abrir el archivo con file://) se asume desarrollo local.
    const host = location.hostname || 'localhost';
    return ['/api/v1', `${protocolo}//${host}:8080/api/v1`];
  },

  async resolver() {
    const candidatas = this.candidatas();
    for (const candidata of candidatas) {
      try {
        // 8 segundos, no 2,5: en una instancia pequena la primera peticion a
        // Spring Boot puede tardar varios segundos y con un margen corto el
        // sondeo fallaba y caia al respaldo.
        const r = await fetch(`${candidata}/health`, { signal: AbortSignal.timeout(8000) });
        if (r.ok) { this.base = candidata; return candidata; }
      } catch { /* se prueba la siguiente */ }
    }
    this.base = candidatas[1];
    return null;
  },

  async post(ruta, cuerpo) {
    const respuesta = await fetch(this.base + ruta, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cuerpo),
    });
    const datos = await respuesta.json().catch(() => null);

    if (!respuesta.ok) {
      // El backend devuelve {mensaje, detalles:{campo:motivo}} en los 400.
      const detalles = datos && datos.detalles ? Object.values(datos.detalles).join('. ') : null;
      throw new Error(detalles || (datos && datos.mensaje) || `Error ${respuesta.status}`);
    }
    return datos;
  },

  async get(ruta) {
    const respuesta = await fetch(this.base + ruta);
    if (!respuesta.ok) throw new Error(`Error ${respuesta.status}`);
    return respuesta.json();
  },
};

const ChatApi = {
  endpoint: '/n8n/webhook/chat-support',

  limpiarRespuesta(texto) {
    return String(texto)
      .replace(/^\s*#+\s*/gm, '')
      .replace(/^\s*\*\s+/gm, '- ')
      .replace(/\*/g, '')
      .trim();
  },

  async preguntar(pregunta, informe) {
    const contexto = informe ? {
      perfil_financiero: informe.resultado.perfil_financiero,
      probabilidad: informe.resultado.probabilidad,
      resumen_gastos: informe.resultado.resumen_gastos,
      recomendaciones: informe.resultado.recomendaciones,
      factores: informe.resultado.factores,
      ingreso_mensual: informe.entrada.ingreso_mensual,
      nivel_endeudamiento: informe.entrada.nivel_endeudamiento,
      frecuencia_ahorro: informe.entrada.frecuencia_ahorro,
      moneda: informe.entrada.moneda,
      modo_degradado: informe.resultado.modo_degradado,
    } : null;

    const mensaje = contexto
      ? `${pregunta}\n\nCONTEXTO FINANCIERO DEL USUARIO (úsalo para personalizar la respuesta):\n${JSON.stringify(contexto)}`
      : pregunta;

    const respuesta = await fetch(this.endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chatInput: mensaje }),
      signal: AbortSignal.timeout(90000),
    });
    const datos = await respuesta.json().catch(() => null);
    if (!respuesta.ok) throw new Error(datos?.message || `El chat no está disponible (${respuesta.status}).`);
    const texto = datos?.respuesta || datos?.output || 'No pude generar una respuesta en este momento.';
    return this.limpiarRespuesta(texto);
  },
};

// ------------------------------------------------------------ estado sistema

async function actualizarEstado() {
  const punto = $('#estado-punto');
  const texto = $('#estado-texto');

  const resuelta = await Api.resolver();
  $('#pie-api').textContent = `API: ${Api.base}`;

  if (!resuelta) {
    punto.className = 'latido mal';
    texto.textContent = 'Backend no disponible';
    return;
  }

  try {
    const estado = await Api.get('/ml-status');
    const modelo = estado.modelo || {};
    if (estado.disponible) {
      punto.className = 'latido ok';
      const version = modelo.version ? ` v${modelo.version}` : '';
      const origen = modelo.origen === 'oci' ? ' · OCI' : '';
      texto.textContent = `Modelo activo${version}${origen}`;
    } else {
      punto.className = 'latido aviso';
      texto.textContent = 'Modo degradado';
    }
  } catch {
    punto.className = 'latido aviso';
    texto.textContent = 'Modelo desconocido';
  }
}

// ------------------------------------------------------------ transacciones

function filaTransaccion(descripcion = '', valor = '') {
  const fila = crear('div', { class: 'transaccion' });
  const entradaDescripcion = crear('input', {
    type: 'text', placeholder: 'Descripción', value: descripcion, maxlength: '200',
  });
  const entradaValor = crear('input', {
    type: 'number', placeholder: 'Monto', min: '0.01', step: '0.01', value: valor,
  });
  const quitar = crear('button', { type: 'button', class: 'quitar', title: 'Quitar' });
  quitar.append(icono('x'));

  quitar.addEventListener('click', () => {
    fila.classList.add('saliendo');
    setTimeout(() => {
      fila.remove();
      // Siempre queda al menos una fila; si no, no hay dónde escribir.
      if (!$('#transacciones').children.length) agregarFila();
      actualizarContador();
    }, sinMovimiento() ? 0 : 240);
  });

  entradaDescripcion.addEventListener('input', actualizarContador);
  entradaValor.addEventListener('input', actualizarContador);

  fila.append(entradaDescripcion, entradaValor, quitar);
  return fila;
}

function agregarFila(descripcion, valor) {
  $('#transacciones').append(filaTransaccion(descripcion, valor));
  actualizarContador();
}

function actualizarContador() {
  const n = leerTransacciones().length;
  $('#contador-tx').textContent = n;
}

function leerTransacciones() {
  return $$('#transacciones .transaccion')
    .filter((fila) => !fila.classList.contains('saliendo'))
    .map((fila) => {
      const [descripcion, valor] = fila.querySelectorAll('input');
      return { descripcion: descripcion.value.trim(), valor: parseFloat(valor.value) };
    })
    .filter((t) => t.descripcion && Number.isFinite(t.valor) && t.valor > 0);
}

function cargarEjemplo(nombre) {
  const ejemplo = EJEMPLOS[nombre];
  $('#ingreso').value = formatearMonto(ejemplo.ingreso);
  actualizarSimboloMoneda();
  ponerDeuda(ejemplo.deuda);
  ponerAhorro(ejemplo.ahorro);
  $('#transacciones').replaceChildren();
  ejemplo.transacciones.forEach(([d, v], i) => {
    const fila = filaTransaccion(d, v);
    fila.style.animationDelay = `${i * 45}ms`;
    $('#transacciones').append(fila);
  });
  actualizarContador();
}

function ponerDeuda(valor) {
  $('#deuda').value = valor;
  $('#deuda-salida').textContent = `${valor}%`;
  $('#deuda').style.setProperty('--progreso', `${valor}%`);
}

function ponerAhorro(valor) {
  const botones = $$('#ahorro-grupo .segmento');
  const indice = botones.findIndex((b) => b.dataset.valor === valor);
  if (indice < 0) return;
  botones.forEach((b) => b.classList.remove('activo'));
  botones[indice].classList.add('activo');
  $('#ahorro-pildora').style.transform = `translateX(calc(${indice * 100}% + ${indice * 2}px))`;
}

function ahorroSeleccionado() {
  const activo = $('#ahorro-grupo .segmento.activo');
  return activo ? activo.dataset.valor : 'Media';
}

/** Importa un CSV con cabecera descripcion,valor (o las dos primeras columnas). */
function importarCsv(texto) {
  const lineas = texto.split(/\r?\n/).filter((l) => l.trim());
  if (!lineas.length) return 0;

  const separador = (lineas[0].match(/;/g) || []).length > (lineas[0].match(/,/g) || []).length ? ';' : ',';
  const cabecera = lineas[0].toLowerCase();
  const tieneCabecera = cabecera.includes('descripcion') || cabecera.includes('descripción');

  let iDescripcion = 0;
  let iValor = 1;
  if (tieneCabecera) {
    const columnas = cabecera.split(separador).map((c) => c.trim());
    const buscar = (...nombres) => columnas.findIndex((c) => nombres.some((n) => c.includes(n)));
    iDescripcion = Math.max(0, buscar('descripcion', 'descripción', 'concepto'));
    iValor = Math.max(1, buscar('valor', 'monto', 'importe'));
    lineas.shift();
  }

  $('#transacciones').replaceChildren();
  let importadas = 0;

  for (const linea of lineas) {
    const celdas = linea.split(separador).map((c) => c.trim().replace(/^"|"$/g, ''));
    const descripcion = celdas[iDescripcion];
    // Se acepta el formato local (1.234,56) y el anglosajón (1234.56).
    const bruto = (celdas[iValor] || '').replace(/\s/g, '').replace(/\.(?=\d{3}\b)/g, '').replace(',', '.');
    const valor = Math.abs(parseFloat(bruto));

    if (descripcion && Number.isFinite(valor) && valor > 0) {
      agregarFila(descripcion, valor);
      importadas += 1;
    }
  }

  if (!importadas) agregarFila();
  actualizarContador();
  return importadas;
}

// ------------------------------------------------------------------ gráficos

function dibujarMedidor(probabilidad, color) {
  const TAMANO = 132;
  const RADIO = 55;
  const GROSOR = 11;
  const perimetro = 2 * Math.PI * RADIO;
  const centro = TAMANO / 2;

  const lienzo = svg('svg', { viewBox: `0 0 ${TAMANO} ${TAMANO}`, width: TAMANO, height: TAMANO });

  lienzo.append(svg('circle', {
    cx: centro, cy: centro, r: RADIO, fill: 'none',
    stroke: 'currentColor', 'stroke-opacity': '.12', 'stroke-width': GROSOR,
  }));

  const arco = svg('circle', {
    cx: centro, cy: centro, r: RADIO, fill: 'none',
    stroke: color, 'stroke-width': GROSOR, 'stroke-linecap': 'round',
    'stroke-dasharray': `0 ${perimetro}`,
    transform: `rotate(-90 ${centro} ${centro})`,
  });
  arco.style.filter = `drop-shadow(0 0 7px ${color})`;
  lienzo.append(arco);

  const numero = svg('text', {
    x: centro, y: centro + 1, 'text-anchor': 'middle', 'dominant-baseline': 'middle',
    fill: 'currentColor', 'font-size': '25', 'font-weight': '680',
  });
  numero.textContent = `${Math.round(probabilidad * 100)}%`;
  lienzo.append(numero);

  const pie = svg('text', {
    x: centro, y: centro + 24, 'text-anchor': 'middle',
    fill: 'currentColor', 'font-size': '9.5', 'fill-opacity': '.55',
    'letter-spacing': '.08em',
  });
  pie.textContent = 'CONFIANZA';
  lienzo.append(pie);

  // El barrido se lanza en el siguiente fotograma: si se aplicara el valor
  // final en el mismo, no habría transición desde la que animar.
  if (!sinMovimiento()) {
    arco.style.transition = 'stroke-dasharray 1.1s cubic-bezier(.22,1,.36,1)';
    requestAnimationFrame(() => requestAnimationFrame(() => {
      arco.setAttribute('stroke-dasharray', `${perimetro * probabilidad} ${perimetro}`);
    }));
  } else {
    arco.setAttribute('stroke-dasharray', `${perimetro * probabilidad} ${perimetro}`);
  }

  return lienzo;
}

function dibujarDona(resumen, moneda) {
  const TAMANO = 210;
  const RADIO_EXTERIOR = 98;
  const RADIO_INTERIOR = 62;
  const centro = TAMANO / 2;
  const SEPARACION = 0.022;   // hueco en radianes entre sectores

  const entradas = CATEGORIAS
    .map((c) => [c, resumen[c] || 0])
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1]);

  const total = entradas.reduce((suma, [, v]) => suma + v, 0);
  const lienzo = svg('svg', { viewBox: `0 0 ${TAMANO} ${TAMANO}`, width: TAMANO, height: TAMANO });

  if (!total) return lienzo;

  // Un único segmento no se puede dibujar con un arco de 360 grados: el punto
  // inicial y el final coinciden y el path queda vacío. Se usa un anillo.
  if (entradas.length === 1) {
    const anillo = svg('circle', {
      cx: centro, cy: centro, r: (RADIO_EXTERIOR + RADIO_INTERIOR) / 2, fill: 'none',
      stroke: colorCategoria(entradas[0][0]),
      'stroke-width': RADIO_EXTERIOR - RADIO_INTERIOR,
    });
    anillo.setAttribute('data-sector', entradas[0][0]);
    lienzo.append(anillo);
  } else {
    let angulo = -Math.PI / 2;
    entradas.forEach(([categoria, valor], indice) => {
      const barrido = (valor / total) * 2 * Math.PI;
      const desde = angulo + SEPARACION / 2;
      const hasta = angulo + barrido - SEPARACION / 2;
      const arcoLargo = (hasta - desde) > Math.PI ? 1 : 0;

      const punto = (radio, a) => [
        (centro + radio * Math.cos(a)).toFixed(2),
        (centro + radio * Math.sin(a)).toFixed(2),
      ];
      const [x1, y1] = punto(RADIO_EXTERIOR, desde);
      const [x2, y2] = punto(RADIO_EXTERIOR, hasta);
      const [x3, y3] = punto(RADIO_INTERIOR, hasta);
      const [x4, y4] = punto(RADIO_INTERIOR, desde);

      const sector = svg('path', {
        d: `M ${x1} ${y1} A ${RADIO_EXTERIOR} ${RADIO_EXTERIOR} 0 ${arcoLargo} 1 ${x2} ${y2} `
         + `L ${x3} ${y3} A ${RADIO_INTERIOR} ${RADIO_INTERIOR} 0 ${arcoLargo} 0 ${x4} ${y4} Z`,
        fill: colorCategoria(categoria),
      });
      sector.setAttribute('data-sector', categoria);
      sector.style.animationDelay = `${indice * 70}ms`;

      const titulo = svg('title');
      titulo.textContent = `${NOMBRE_CATEGORIA[categoria] || categoria}: `
        + `${dineroMoneda(valor, moneda)} (${Math.round(valor / total * 100)}%)`;
      sector.append(titulo);

      lienzo.append(sector);
      angulo += barrido;
    });
  }

  const etiqueta = svg('text', {
    x: centro, y: centro - 7, 'text-anchor': 'middle',
    fill: 'currentColor', 'font-size': '9', 'fill-opacity': '.55', 'letter-spacing': '.09em',
    class: 'dona-total',
  });
  etiqueta.textContent = 'GASTO TOTAL';
  lienzo.append(etiqueta);

  const monto = svg('text', {
    x: centro, y: centro + 15, 'text-anchor': 'middle',
    fill: 'currentColor', 'font-size': '21', 'font-weight': '680',
    class: 'dona-total',
  });
  lienzo.append(monto);
  animarNumero(monto, total, (v) => dineroMoneda(v, moneda), 1000);

  return lienzo;
}

function dibujarEvolucion(historial) {
  const ANCHO = 760;
  const ALTO = 220;
  const MARGEN = { arriba: 18, derecha: 18, abajo: 30, izquierda: 46 };

  const puntos = historial.slice().reverse();
  if (puntos.length < 2) return null;

  // Escalado uniforme. Con preserveAspectRatio="none" el viewBox se estira solo
  // en horizontal: los puntos se deforman en elipses y el grosor del trazo deja
  // de ser constante.
  const lienzo = svg('svg', {
    viewBox: `0 0 ${ANCHO} ${ALTO}`,
    style: 'width:100%;height:auto;display:block;max-height:280px',
  });

  const anchoUtil = ANCHO - MARGEN.izquierda - MARGEN.derecha;
  const altoUtil = ALTO - MARGEN.arriba - MARGEN.abajo;
  const maximo = Math.max(1.1, ...puntos.map((p) => p.tasaGasto));

  const x = (i) => MARGEN.izquierda + (i / (puntos.length - 1)) * anchoUtil;
  const y = (v) => MARGEN.arriba + altoUtil - (v / maximo) * altoUtil;

  // Degradado del área bajo la curva.
  const defs = svg('defs');
  const grad = svg('linearGradient', { id: 'gradEvolucion', x1: '0', y1: '0', x2: '0', y2: '1' });
  const p1 = svg('stop', { offset: '0%', 'stop-color': '#7c6cff', 'stop-opacity': '.34' });
  const p2 = svg('stop', { offset: '100%', 'stop-color': '#7c6cff', 'stop-opacity': '0' });
  grad.append(p1, p2);
  defs.append(grad);
  lienzo.append(defs);

  // Referencia: gastar el 100% del ingreso.
  lienzo.append(svg('line', {
    x1: MARGEN.izquierda, y1: y(1), x2: ANCHO - MARGEN.derecha, y2: y(1),
    stroke: 'var(--rojo)', 'stroke-width': 1, 'stroke-dasharray': '5 5', 'stroke-opacity': '.55',
  }));
  const refe = svg('text', {
    x: MARGEN.izquierda + 5, y: y(1) - 6, fill: 'var(--rojo)', 'font-size': '10', 'fill-opacity': '.8',
  });
  refe.textContent = '100% del ingreso';
  lienzo.append(refe);

  const coords = puntos.map((p, i) => [x(i), y(p.tasaGasto)]);

  lienzo.append(svg('path', {
    d: `M ${coords[0][0].toFixed(1)} ${(ALTO - MARGEN.abajo).toFixed(1)} `
     + coords.map(([cx, cy]) => `L ${cx.toFixed(1)} ${cy.toFixed(1)}`).join(' ')
     + ` L ${coords.at(-1)[0].toFixed(1)} ${(ALTO - MARGEN.abajo).toFixed(1)} Z`,
    fill: 'url(#gradEvolucion)',
  }));

  const trazo = coords.map(([cx, cy], i) => `${i ? 'L' : 'M'} ${cx.toFixed(1)} ${cy.toFixed(1)}`).join(' ');
  const linea = svg('path', {
    d: trazo, fill: 'none', stroke: '#7c6cff', 'stroke-width': 2.5,
    'stroke-linejoin': 'round', 'stroke-linecap': 'round',
  });
  lienzo.append(linea);

  // La línea se dibuja de izquierda a derecha con el truco del dasharray.
  if (!sinMovimiento() && typeof linea.getTotalLength === 'function') {
    const largo = linea.getTotalLength();
    linea.style.strokeDasharray = largo;
    linea.style.strokeDashoffset = largo;
    linea.style.transition = 'stroke-dashoffset 1.2s cubic-bezier(.22,1,.36,1)';
    requestAnimationFrame(() => requestAnimationFrame(() => { linea.style.strokeDashoffset = '0'; }));
  }

  puntos.forEach((p, i) => {
    const punto = svg('circle', {
      cx: x(i), cy: y(p.tasaGasto), r: 5,
      fill: COLOR_PERFIL[p.perfil] || 'var(--texto-tenue)',
      stroke: 'var(--lienzo)', 'stroke-width': 2.5,
    });
    const titulo = svg('title');
    titulo.textContent = `${p.perfil} · ${Math.round(p.tasaGasto * 100)}% del ingreso`;
    punto.append(titulo);
    lienzo.append(punto);
  });

  [0, maximo / 2, maximo].forEach((valor) => {
    const marca = svg('text', {
      x: MARGEN.izquierda - 9, y: y(valor) + 3.5, 'text-anchor': 'end',
      fill: 'currentColor', 'font-size': '10', 'fill-opacity': '.5',
    });
    marca.textContent = `${Math.round(valor * 100)}%`;
    lienzo.append(marca);
  });

  return lienzo;
}

// -------------------------------------------------------------------- render

let ultimoInforme = null;

function mostrarResultado(datos, entrada) {
  $('#bienvenida').hidden = true;
  $('#resultado').hidden = false;
  $('#aviso-degradado').hidden = !datos.modo_degradado;

  const perfil = datos.perfil_financiero;
  const tarjeta = $('#tarjeta-perfil');
  tarjeta.className = `vidrio tarjeta-perfil surge ${CLASE_PERFIL[perfil] || ''}`;
  $('#perfil-nombre').textContent = perfil;
  $('#perfil-pie').textContent = RESUMEN_PERFIL[perfil] || '';

  $('#medidor').replaceChildren(
    dibujarMedidor(datos.probabilidad || 0, COLOR_PERFIL[perfil] || 'var(--texto-tenue)'));

  const resumen = datos.resumen_gastos || {};
  const moneda = entrada.moneda || monedaSeleccionada();
  const totalGastos = Object.values(resumen).reduce((s, v) => s + v, 0);
  const tasaGasto = entrada.ingreso_mensual ? totalGastos / entrada.ingreso_mensual : 0;
  const disponible = entrada.ingreso_mensual - totalGastos;

  const indicadores = [
    ['Ingreso mensual', entrada.ingreso_mensual, (v) => dineroMoneda(v, moneda)],
    ['Gasto total', totalGastos, (v) => dineroMoneda(v, moneda)],
    ['Queda disponible', disponible, (v) => dineroMoneda(v, moneda)],
    ['Gastas de tu ingreso', tasaGasto * 100, (v) => `${Math.round(v)}%`],
    ['Endeudamiento', entrada.nivel_endeudamiento, (v) => `${Math.round(v)}%`],
  ];

  $('#indicadores').replaceChildren(...indicadores.map(([titulo, valor, formato], i) => {
    const dd = crear('dd');
    const bloque = crear('dl', { class: 'indicador' }, [crear('dt', { text: titulo }), dd]);
    bloque.style.animationDelay = `${120 + i * 55}ms`;
    animarNumero(dd, valor, formato, 850);
    return bloque;
  }));

  // Dona y leyenda
  $('#dona').replaceChildren(dibujarDona(resumen, moneda));

  const entradas = CATEGORIAS
    .map((c) => [c, resumen[c] || 0])
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1]);

  $('#leyenda').replaceChildren(...entradas.map(([categoria, valor], i) => {
    const marca = crear('span', { class: 'marca-cat' }, [icono(categoria)]);
    marca.style.background = colorCategoria(categoria);

    const monto = crear('span', { class: 'monto' });
    animarNumero(monto, valor, (v) => dineroMoneda(v, moneda), 700);

    const fila = crear('li', {}, [
      marca,
      crear('span', { class: 'nombre', text: NOMBRE_CATEGORIA[categoria] || categoria }),
      monto,
      crear('span', { class: 'pct', text: `${Math.round((valor / totalGastos) * 100)}%` }),
    ]);
    fila.style.animationDelay = `${180 + i * 60}ms`;
    return fila;
  }));

  // Recomendaciones
  $('#recomendaciones').replaceChildren(...(datos.recomendaciones || []).map((r, i) => {
    const fila = crear('li', {}, [
      crear('span', { class: 'num', text: String(i + 1) }),
      crear('span', { text: r }),
    ]);
    fila.style.animationDelay = `${100 + i * 80}ms`;
    return fila;
  }));

  // Factores
  $('#factores').replaceChildren(...(datos.factores || []).map((f, i) => {
    const sube = f.impacto === 'sube_riesgo';
    const fila = crear('li', { class: `factor ${sube ? 'sube' : 'baja'}` }, [
      crear('span', { class: 'fbarra' }),
      crear('span', { class: 'fnombre', text: NOMBRE_FACTOR[f.nombre] || f.nombre }),
      crear('span', { class: 'fvalor', text: decimal.format(f.valor) }),
      crear('span', { class: 'fimpacto', text: sube ? '↑ riesgo' : '↓ riesgo' }),
    ]);
    fila.style.animationDelay = `${100 + i * 80}ms`;
    return fila;
  }));

  ultimoInforme = {
    generado_en: new Date().toISOString(),
    entrada,
    resultado: datos,
    indicadores: {
      gasto_total: totalGastos,
      disponible,
      tasa_gasto: Number(tasaGasto.toFixed(4)),
    },
  };

  guardarEnHistorial({
    fecha: new Date().toISOString(),
    perfil,
    probabilidad: datos.probabilidad,
    ingreso: entrada.ingreso_mensual,
    gasto: totalGastos,
    tasaGasto,
    deuda: entrada.nivel_endeudamiento,
    moneda,
    degradado: !!datos.modo_degradado,
  });
}

function agregarMensajeChat(texto, tipo) {
  const mensaje = crear('div', { class: `chat-mensaje ${tipo}`, text: texto });
  $('#chat-mensajes').append(mensaje);
  mensaje.scrollIntoView({ behavior: sinMovimiento() ? 'auto' : 'smooth', block: 'nearest' });
}

async function enviarPreguntaChat(evento) {
  evento.preventDefault();
  const entrada = $('#chat-pregunta');
  const boton = $('#btn-chat');
  const pregunta = entrada.value.trim();
  if (!pregunta) return;

  agregarMensajeChat(pregunta, 'usuario');
  entrada.value = '';
  boton.classList.add('cargando');
  boton.disabled = true;
  try {
    agregarMensajeChat(await ChatApi.preguntar(pregunta, ultimoInforme), 'asistente');
  } catch (error) {
    agregarMensajeChat(`No pude responder ahora. ${error.message}`, 'error');
  } finally {
    boton.classList.remove('cargando');
    boton.disabled = false;
    entrada.focus();
  }
}

// ---------------------------------------------------------------- exportación

function exportarInforme() {
  if (!ultimoInforme) return;

  const blob = new Blob([JSON.stringify(ultimoInforme, null, 2)], {
    type: 'application/json;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);

  const enlace = document.createElement('a');
  enlace.href = url;
  enlace.download = `financeai-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.append(enlace);
  enlace.click();
  enlace.remove();
  // Sin revocar, el blob queda retenido en memoria mientras viva la pestaña.
  URL.revokeObjectURL(url);
}

// ------------------------------------------------------------------ historial

function leerHistorial() {
  try {
    return JSON.parse(localStorage.getItem(CLAVE_HISTORIAL)) || [];
  } catch {
    return [];
  }
}

function guardarEnHistorial(registro) {
  const historial = leerHistorial();
  historial.unshift(registro);
  try {
    localStorage.setItem(CLAVE_HISTORIAL, JSON.stringify(historial.slice(0, 50)));
  } catch { /* almacenamiento lleno o deshabilitado: no es crítico */ }
  renderHistorial();
}

function renderHistorial() {
  const historial = leerHistorial();
  const contenedorGrafico = $('#grafico-historial');
  const contenedorTabla = $('#tabla-historial');

  if (!historial.length) {
    contenedorGrafico.replaceChildren();
    contenedorTabla.replaceChildren(crear('p', {
      class: 'vacio',
      text: 'Todavía no hay análisis. Ejecuta uno para empezar a ver tu evolución.',
    }));
    return;
  }

  const grafico = dibujarEvolucion(historial);
  contenedorGrafico.replaceChildren(grafico || crear('p', {
    class: 'vacio',
    text: 'Con dos análisis o más aparecerá aquí la línea de evolución.',
  }));

  const tabla = crear('table', { class: 'tabla' });
  tabla.append(crear('thead', {}, [crear('tr', {}, [
    crear('th', { text: 'Fecha' }), crear('th', { text: 'Perfil' }),
    crear('th', { text: 'Ingreso' }), crear('th', { text: 'Gasto' }),
    crear('th', { text: 'Tasa' }), crear('th', { text: 'Deuda' }),
  ])]));

  const cuerpo = crear('tbody');
  historial.slice(0, 12).forEach((r, i) => {
    const insignia = crear('span', { class: 'insignia', text: r.perfil });
    insignia.style.background = COLOR_PERFIL[r.perfil] || 'var(--texto-tenue)';

    const fila = crear('tr', {}, [
      crear('td', { text: new Date(r.fecha).toLocaleString('es', { dateStyle: 'short', timeStyle: 'short' }) }),
      crear('td', {}, [insignia]),
      crear('td', { class: 'num', text: dineroMoneda(r.ingreso, r.moneda) }),
      crear('td', { class: 'num', text: dineroMoneda(r.gasto, r.moneda) }),
      crear('td', { class: 'num', text: `${Math.round(r.tasaGasto * 100)}%` }),
      crear('td', { class: 'num', text: `${r.deuda}%` }),
    ]);
    fila.style.animationDelay = `${i * 40}ms`;
    cuerpo.append(fila);
  });
  tabla.append(cuerpo);
  contenedorTabla.replaceChildren(crear('div', { class: 'tabla-envoltura' }, [tabla]));
}

// ------------------------------------------------------------- clasificador

function parsearLineasClasificador(texto) {
  return texto.split(/\r?\n/)
    .map((linea) => linea.trim())
    .filter(Boolean)
    .map((linea) => {
      // "descripcion, monto" — se parte por la ÚLTIMA coma, porque la propia
      // descripción puede llevar comas.
      const corte = linea.lastIndexOf(',');
      if (corte > 0) {
        const valor = parseFloat(linea.slice(corte + 1).trim().replace(',', '.'));
        if (Number.isFinite(valor) && valor > 0) {
          return { descripcion: linea.slice(0, corte).trim(), valor };
        }
      }
      return { descripcion: linea, valor: 1 };
    })
    .filter((t) => t.descripcion);
}

async function clasificar() {
  const boton = $('#btn-clasificar');
  const salida = $('#resultado-clasificador');
  const transacciones = parsearLineasClasificador($('#texto-clasificar').value);

  if (!transacciones.length) {
    tostada('Escribe al menos una descripción.');
    return;
  }

  boton.classList.add('cargando');
  boton.disabled = true;
  try {
    const datos = await Api.post('/clasificar-transacciones', { transacciones });

    const tabla = crear('table', { class: 'tabla' });
    tabla.append(crear('thead', {}, [crear('tr', {}, [
      crear('th', { text: 'Descripción' }), crear('th', { text: 'Categoría' }),
      crear('th', { text: 'Estado' }), crear('th', { text: 'Confianza' }),
      crear('th', { text: 'Top 3' }), crear('th', { text: 'Monto' }),
    ])]));

    const cuerpo = crear('tbody');
    datos.transacciones_clasificadas.forEach((t, i) => {
      const confianza = t.confianza || 0;

      const insignia = crear('span', { class: 'insignia' }, [
        icono(t.categoria),
        crear('span', { text: NOMBRE_CATEGORIA[t.categoria] || t.categoria }),
      ]);
      insignia.style.background = colorCategoria(t.categoria);

      // Estado de confianza explícito (Fase 12): aceptado | requiere_revision | otras.
      const insigniaEstado = crear('span', {
        class: `insignia-estado ${CLASE_ESTADO_CONFIANZA[t.estado_confianza] || ''}`,
        text: NOMBRE_ESTADO_CONFIANZA[t.estado_confianza] || t.estado_confianza || '—',
      });

      const relleno = crear('span', { class: 'relleno' });
      const medida = crear('span', { class: `medida-confianza ${confianza < 0.5 ? 'baja' : ''}` }, [
        crear('span', { class: 'pista' }, [relleno]),
        crear('span', { class: 'pct', text: `${Math.round(confianza * 100)}%` }),
      ]);
      setTimeout(() => { relleno.style.width = `${confianza * 100}%`; }, 120 + i * 60);

      // Top-3 categorías candidatas (Fase 16), con la confianza del modelo
      // para cada una. En modo reglas/degradado trae un solo elemento.
      const top3 = crear('div', { class: 'top3-lista' }, (t.top3 || []).map((candidato) => {
        const chip = crear('span', { class: 'top3-chip' }, [
          crear('span', { class: 'top3-punto' }),
          crear('span', { text: NOMBRE_CATEGORIA[candidato.categoria] || candidato.categoria }),
          crear('span', { class: 'top3-pct', text: `${Math.round((candidato.confianza || 0) * 100)}%` }),
        ]);
        chip.style.setProperty('--color-cat', colorCategoria(candidato.categoria));
        return chip;
      }));

      const fila = crear('tr', {}, [
        crear('td', { text: t.descripcion }),
        crear('td', {}, [insignia]),
        crear('td', {}, [insigniaEstado]),
        crear('td', {}, [medida]),
        crear('td', {}, [top3]),
        crear('td', { class: 'num', text: dineroMoneda(t.valor) }),
      ]);
      fila.style.animationDelay = `${i * 45}ms`;
      cuerpo.append(fila);
    });
    tabla.append(cuerpo);

    const nodos = [crear('div', { class: 'tabla-envoltura' }, [tabla])];
    if (datos.modo_degradado) {
      nodos.unshift(crear('div', { class: 'aviso' }, [
        icono('alerta'),
        crear('span', { text: 'Clasificado con reglas locales: el servicio de modelos no respondió.' }),
      ]));
    }
    salida.replaceChildren(...nodos);
  } catch (e) {
    tostada(e.message);
  } finally {
    boton.classList.remove('cargando');
    boton.disabled = false;
  }
}

// ----------------------------------------------------------------- métricas

/**
 * Tarjetas de comparación baseline (Fase 1/2/16): partición aleatoria,
 * comercio no visto y CV agrupada por comercio. Las tres miden lo mismo
 * (accuracy y F1 macro) sobre particiones distintas, así que se muestran
 * lado a lado en vez de en un gráfico.
 */
function renderBaselineComparativo(baseline, cvAgrupada) {
  const tarjetas = [
    {
      titulo: 'Partición aleatoria',
      nota: 'Optimista: mezcla el mismo comercio en entrenamiento y prueba.',
      tono: 'ambar',
      metricas: [
        ['Accuracy', baseline.particion_aleatoria.accuracy],
        ['F1 macro', baseline.particion_aleatoria.f1_macro],
      ],
    },
    {
      titulo: 'Comercio no visto',
      nota: 'Realista: separa por comercio, sin fuga de información entre partes.',
      tono: 'rojo',
      metricas: [
        ['Accuracy', baseline.comercio_no_visto.accuracy],
        ['F1 macro', baseline.comercio_no_visto.f1_macro],
      ],
    },
    {
      titulo: 'CV agrupada por comercio',
      nota: 'Media ± desviación estándar entre 5 particiones agrupadas por comercio.',
      tono: 'verde',
      metricas: [
        ['Accuracy', cvAgrupada.accuracy.media, cvAgrupada.accuracy.desviacion_estandar],
        ['F1 macro', cvAgrupada.f1_macro.media, cvAgrupada.f1_macro.desviacion_estandar],
      ],
    },
  ];

  return tarjetas.map((t, i) => {
    const tarjeta = crear('div', { class: `metrica-tarjeta tono-${t.tono}` }, [
      crear('h4', { text: t.titulo }),
      crear('p', { class: 'ayuda', text: t.nota }),
      ...t.metricas.map(([nombre, media, desviacion]) => crear('div', { class: 'metrica-fila' }, [
        crear('span', { class: 'metrica-nombre', text: nombre }),
        crear('span', {
          class: 'metrica-valor',
          text: `${(media * 100).toFixed(1)}%${desviacion != null ? ` ± ${(desviacion * 100).toFixed(1)}` : ''}`,
        }),
      ])),
    ]);
    tarjeta.style.animationDelay = `${i * 70}ms`;
    return tarjeta;
  });
}

/**
 * Matriz de confusión 8x8 (Fase 4) como tabla con celdas teñidas: color de
 * la categoría real (fila), más opaco cuantas más transacciones cayeron ahí.
 * La diagonal (aciertos) se resalta con un anillo en vez de solo el color,
 * para que se distinga incluso en modo claro/oscuro y para quien no perciba
 * bien el color.
 */
function dibujarMatrizConfusion({ categorias, matriz }) {
  const maximo = Math.max(1, ...matriz.flat());

  const filaCabecera = crear('tr', {}, [crear('th', { class: 'matriz-esquina', text: 'Real \\ Predicho' })]);
  categorias.forEach((c) => {
    const celda = crear('th', { title: NOMBRE_CATEGORIA[c] || c });
    const marca = crear('span', { class: 'matriz-col-icono' }, [icono(c)]);
    marca.style.background = colorCategoria(c);
    celda.append(marca);
    filaCabecera.append(celda);
  });

  const cuerpo = crear('tbody');
  categorias.forEach((categoriaReal, i) => {
    const marca = crear('span', { class: 'marca-cat matriz-marca-mini' }, [icono(categoriaReal)]);
    marca.style.background = colorCategoria(categoriaReal);
    const encabezadoFila = crear('th', { class: 'matriz-fila-th', scope: 'row' }, [
      crear('span', { class: 'matriz-fila-nombre' }, [marca, crear('span', { text: NOMBRE_CATEGORIA[categoriaReal] || categoriaReal })]),
    ]);

    const fila = crear('tr', {}, [encabezadoFila]);
    matriz[i].forEach((valor, j) => {
      const intensidad = valor / maximo;
      const celda = crear('td', {
        class: `matriz-celda${i === j ? ' matriz-diagonal' : ''}`,
        text: String(valor),
        title: `${NOMBRE_CATEGORIA[categoriaReal] || categoriaReal} clasificado como `
          + `${NOMBRE_CATEGORIA[categorias[j]] || categorias[j]}: ${valor}`,
      });
      celda.style.background = `color-mix(in srgb, ${colorCategoria(categoriaReal)} ${Math.round(intensidad * 80)}%, transparent)`;
      fila.append(celda);
    });
    fila.style.animationDelay = `${i * 45}ms`;
    cuerpo.append(fila);
  });

  const tabla = crear('table', { class: 'matriz' }, [crear('thead', {}, [filaCabecera]), cuerpo]);
  return crear('div', { class: 'matriz-envoltura' }, [tabla]);
}

/** Tabla del benchmark de modelos clásicos (Fase 9/10). Los valores ya llegan
 *  formateados como texto ("0.4276 +/- 0.0733") desde metricas_resumen.json;
 *  solo se cambia el separador por el signo ± para que se lea mejor. */
function renderBenchmarkTabla(benchmark) {
  const tabla = crear('table', { class: 'tabla' });
  tabla.append(crear('thead', {}, [crear('tr', {}, [
    crear('th', { text: 'Modelo / variante' }),
    crear('th', { text: 'Accuracy' }),
    crear('th', { text: 'F1 macro' }),
    crear('th', { text: 'F1 weighted' }),
    crear('th', { text: 'Balanced accuracy' }),
  ])]));

  const cuerpo = crear('tbody');
  benchmark.forEach((fila, i) => {
    const tr = crear('tr', {}, [
      crear('td', { text: fila.modelo }),
      crear('td', { class: 'num', text: String(fila.accuracy).replace('+/-', '±') }),
      crear('td', { class: 'num', text: String(fila.f1_macro).replace('+/-', '±') }),
      crear('td', { class: 'num', text: String(fila.f1_weighted).replace('+/-', '±') }),
      crear('td', { class: 'num', text: String(fila.balanced_accuracy).replace('+/-', '±') }),
    ]);
    tr.style.animationDelay = `${i * 35}ms`;
    cuerpo.append(tr);
  });
  tabla.append(cuerpo);
  return crear('div', { class: 'tabla-envoltura' }, [tabla]);
}

/**
 * Curva coverage-vs-accuracy (Fase 5/12): dos líneas (cobertura y exactitud
 * en lo aceptado) contra el umbral de confianza, con los umbrales de la
 * estrategia de abstención marcados. Mismo esqueleto que dibujarEvolucion.
 */
function dibujarCurvaCobertura(puntosCobertura) {
  if (!Array.isArray(puntosCobertura) || puntosCobertura.length < 2) return null;

  const ANCHO = 760;
  const ALTO = 240;
  const MARGEN = { arriba: 22, derecha: 18, abajo: 30, izquierda: 44 };

  const puntos = puntosCobertura.slice().sort((a, b) => a.umbral - b.umbral);
  const anchoUtil = ANCHO - MARGEN.izquierda - MARGEN.derecha;
  const altoUtil = ALTO - MARGEN.arriba - MARGEN.abajo;
  const maximoUmbral = Math.max(1, ...puntos.map((p) => p.umbral));

  const lienzo = svg('svg', {
    viewBox: `0 0 ${ANCHO} ${ALTO}`,
    style: 'width:100%;height:auto;display:block;max-height:300px',
  });

  const x = (u) => MARGEN.izquierda + (u / maximoUmbral) * anchoUtil;
  const y = (v) => MARGEN.arriba + altoUtil - v * altoUtil;

  // Umbrales de la estrategia de abstención.
  [
    [UMBRAL_REQUIERE_REVISION, 'var(--ambar)', 'requiere_revision ≥ 0.5'],
    [UMBRAL_ACEPTADO, 'var(--verde)', 'aceptado ≥ 0.8'],
  ].forEach(([umbral, color, etiqueta]) => {
    if (umbral > maximoUmbral) return;
    lienzo.append(svg('line', {
      x1: x(umbral), y1: MARGEN.arriba, x2: x(umbral), y2: ALTO - MARGEN.abajo,
      stroke: color, 'stroke-width': 1, 'stroke-dasharray': '4 4', 'stroke-opacity': '.6',
    }));
    const texto = svg('text', {
      x: x(umbral) + 4, y: MARGEN.arriba + 10, fill: color, 'font-size': '9.5', 'fill-opacity': '.9',
    });
    texto.textContent = etiqueta;
    lienzo.append(texto);
  });

  const dibujarSerie = (clave, color) => {
    const coords = puntos.map((p) => [x(p.umbral), y(p[clave])]);
    const trazo = coords.map(([cx, cy], i) => `${i ? 'L' : 'M'} ${cx.toFixed(1)} ${cy.toFixed(1)}`).join(' ');
    const linea = svg('path', {
      d: trazo, fill: 'none', stroke: color, 'stroke-width': 2.5,
      'stroke-linejoin': 'round', 'stroke-linecap': 'round',
    });
    lienzo.append(linea);

    coords.forEach(([cx, cy], i) => {
      const punto = svg('circle', { cx, cy, r: 3.6, fill: color, stroke: 'var(--lienzo)', 'stroke-width': 1.5 });
      const titulo = svg('title');
      const etiquetaSerie = clave === 'coverage' ? 'cobertura' : 'exactitud en lo aceptado';
      titulo.textContent = `umbral ${puntos[i].umbral.toFixed(2)} · ${etiquetaSerie}: `
        + `${Math.round(puntos[i][clave] * 100)}%`;
      punto.append(titulo);
      lienzo.append(punto);
    });

    if (!sinMovimiento() && typeof linea.getTotalLength === 'function') {
      const largo = linea.getTotalLength();
      linea.style.strokeDasharray = String(largo);
      linea.style.strokeDashoffset = String(largo);
      linea.style.transition = 'stroke-dashoffset 1.1s cubic-bezier(.22,1,.36,1)';
      requestAnimationFrame(() => requestAnimationFrame(() => { linea.style.strokeDashoffset = '0'; }));
    }
  };

  dibujarSerie('coverage', 'var(--acento-2)');
  dibujarSerie('accuracy_aceptadas', '#7c6cff');

  [0, .5, 1].forEach((valor) => {
    const marca = svg('text', {
      x: MARGEN.izquierda - 9, y: y(valor) + 3.5, 'text-anchor': 'end',
      fill: 'currentColor', 'font-size': '10', 'fill-opacity': '.5',
    });
    marca.textContent = `${Math.round(valor * 100)}%`;
    lienzo.append(marca);
  });

  puntos.map((p) => p.umbral).forEach((valor) => {
    const marca = svg('text', {
      x: x(valor), y: ALTO - MARGEN.abajo + 16, 'text-anchor': 'middle',
      fill: 'currentColor', 'font-size': '9.5', 'fill-opacity': '.5',
    });
    marca.textContent = valor.toFixed(1);
    lienzo.append(marca);
  });

  return lienzo;
}

let metricasCache = null;

function renderMetricas(datos) {
  if (datos.baseline && datos.cv_agrupada) {
    $('#metricas-baseline').replaceChildren(...renderBaselineComparativo(datos.baseline, datos.cv_agrupada));
  }
  if (datos.matriz_confusion) {
    $('#metricas-matriz').replaceChildren(dibujarMatrizConfusion(datos.matriz_confusion));
  }
  if (Array.isArray(datos.benchmark)) {
    $('#metricas-benchmark').replaceChildren(renderBenchmarkTabla(datos.benchmark));
  }
  if (datos.calibracion?.coverage_vs_accuracy) {
    const grafico = dibujarCurvaCobertura(datos.calibracion.coverage_vs_accuracy);
    $('#metricas-cobertura').replaceChildren(grafico || crear('p', {
      class: 'vacio',
      text: 'No hay suficientes puntos para dibujar la curva de cobertura.',
    }));
  }
}

/** Carga GET /metricas-modelo (Fase 16, proxy del backend Java hacia
 *  srv-python). Igual que /ml-status en otras pestañas: si el servicio no
 *  responde o devuelve un cuerpo vacío, se avisa sin romper el resto de la
 *  página. Se cachea en memoria porque el resumen no cambia entre pestañas. */
async function cargarMetricas() {
  const estado = $('#metricas-estado');
  const estadoTexto = $('#metricas-estado-texto');
  const cuerpo = $('#metricas-cuerpo');

  if (metricasCache) {
    renderMetricas(metricasCache);
    estado.hidden = true;
    cuerpo.hidden = false;
    return;
  }

  estado.hidden = false;
  cuerpo.hidden = true;
  estadoTexto.textContent = 'Cargando métricas del modelo…';

  try {
    if (!Api.base) await Api.resolver();
    const datos = await Api.get('/metricas-modelo');
    if (!datos || !Object.keys(datos).length) {
      estadoTexto.textContent = 'Las métricas del modelo no están disponibles en este momento.';
      return;
    }
    metricasCache = datos;
    renderMetricas(datos);
    estado.hidden = true;
    cuerpo.hidden = false;
  } catch (e) {
    estadoTexto.textContent = `No se pudieron cargar las métricas del modelo. ${e.message}`;
  }
}

// -------------------------------------------------------------------- eventos

async function enviarAnalisis(evento) {
  evento.preventDefault();

  const boton = $('#btn-analizar');
  const transacciones = leerTransacciones();

  if (!transacciones.length) {
    tostada('Añade al menos una transacción con descripción y monto mayor que cero.');
    return;
  }

  const peticion = {
    ingreso_mensual: leerMonto($('#ingreso').value),
    nivel_endeudamiento: parseInt($('#deuda').value, 10),
    frecuencia_ahorro: ahorroSeleccionado(),
    transacciones,
  };
  const entrada = { ...peticion, moneda: monedaSeleccionada() };

  boton.classList.add('cargando');
  boton.disabled = true;
  try {
    const datos = await Api.post('/analisis-financiero', peticion);
    mostrarResultado(datos, entrada);
  } catch (e) {
    tostada(e.message);
  } finally {
    boton.classList.remove('cargando');
    boton.disabled = false;
  }
}

function moverIndicadorPestana(pestana) {
  const indicador = $('#pestana-indicador');
  indicador.style.width = `${pestana.offsetWidth}px`;
  indicador.style.transform = `translateX(${pestana.offsetLeft - 5}px)`;
}

function aplicarTema(tema) {
  document.documentElement.dataset.tema = tema;
  try { localStorage.setItem(CLAVE_TEMA, tema); } catch { /* modo privado */ }
}

function inicializar() {
  // Tema: preferencia guardada, si no la del sistema.
  let temaGuardado = null;
  try { temaGuardado = localStorage.getItem(CLAVE_TEMA); } catch { /* ignorado */ }
  const prefiereClaro = typeof matchMedia === 'function' && matchMedia('(prefers-color-scheme: light)').matches;
  aplicarTema(temaGuardado || (prefiereClaro ? 'claro' : 'oscuro'));

  $('#btn-tema').addEventListener('click', () => {
    aplicarTema(document.documentElement.dataset.tema === 'claro' ? 'oscuro' : 'claro');
  });

  // Pestañas
  $$('.pestana').forEach((pestana) => {
    pestana.addEventListener('click', () => {
      $$('.pestana').forEach((p) => p.classList.remove('activa'));
      $$('.panel').forEach((p) => p.classList.remove('activo'));
      pestana.classList.add('activa');
      $(`#${pestana.dataset.panel}`).classList.add('activo');
      moverIndicadorPestana(pestana);
      // El gráfico de evolución se remide al mostrarse: dibujado dentro de un
      // panel oculto, getTotalLength y offsetWidth devuelven 0.
      if (pestana.dataset.panel === 'panel-historial') renderHistorial();
      if (pestana.dataset.panel === 'panel-metricas') cargarMetricas();
    });
  });

  $('#deuda').addEventListener('input', (e) => ponerDeuda(e.target.value));
  $('#moneda').addEventListener('change', () => {
    actualizarSimboloMoneda();
    actualizarCampoIngreso();
  });
  $('#ingreso').addEventListener('focus', () => actualizarCampoIngreso(false));
  $('#ingreso').addEventListener('blur', () => actualizarCampoIngreso());

  $$('#ahorro-grupo .segmento').forEach((segmento) => {
    segmento.addEventListener('click', () => ponerAhorro(segmento.dataset.valor));
  });

  $('#btn-agregar').addEventListener('click', () => agregarFila());
  $('#btn-csv').addEventListener('click', () => $('#archivo-csv').click());

  $('#archivo-csv').addEventListener('change', async (e) => {
    const archivo = e.target.files[0];
    if (!archivo) return;
    const importadas = importarCsv(await archivo.text());
    $('#ayuda-csv').textContent = importadas
      ? `${importadas} transacciones importadas de ${archivo.name}.`
      : `No se pudo leer ninguna transacción de ${archivo.name}.`;
    e.target.value = '';
  });

  $$('[data-ejemplo]').forEach((chip) => {
    chip.addEventListener('click', () => cargarEjemplo(chip.dataset.ejemplo));
  });

  $('#formulario').addEventListener('submit', enviarAnalisis);
  $('#btn-clasificar').addEventListener('click', clasificar);
  $('#btn-exportar').addEventListener('click', exportarInforme);
  $('#btn-imprimir').addEventListener('click', () => window.print());
  $('#chat-form').addEventListener('submit', enviarPreguntaChat);

  $('#btn-limpiar-historial').addEventListener('click', () => {
    localStorage.removeItem(CLAVE_HISTORIAL);
    renderHistorial();
  });

  cargarEjemplo('saludable');
  actualizarSimboloMoneda();
  actualizarCampoIngreso();
  renderHistorial();
  moverIndicadorPestana($('.pestana.activa'));
  window.addEventListener('resize', () => moverIndicadorPestana($('.pestana.activa')));
  actualizarEstado();
}

document.addEventListener('DOMContentLoaded', inicializar);
