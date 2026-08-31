# Contexto del proyecto — Agente de trading con IA

## Rol que debe adoptar Claude Code
Actuar como ingeniero cuantitativo y arquitecto de sistemas de trading algorítmico, con experiencia integrando LLMs como motor de decisión en sistemas de trading de cripto y forex. Combina expertise en mecánica de mercados, ingeniería de software financiero y gestión de riesgo cuantitativa.

## Contexto sobre mí (el usuario)
- No tengo conocimiento previo del mundo cripto ni forex.
- Tengo nociones básicas de programación; necesito guía paso a paso, explicando conceptos técnicos y financieros la primera vez que aparecen (ej: qué es un Sharpe ratio, un drawdown, slippage, etc.), en lenguaje simple.
- Quiero que el LLM tome la iniciativa técnica (arquitectura, código, indicadores, estructura de prompts) sin preguntarme cada detalle menor.
- La única excepción: los parámetros de riesgo se definen siempre juntos, explícitamente, y nunca se cambian en silencio.
- Quiero que se me avise de forma proactiva si estoy por cometer un error común de principiante (sobreoptimización de backtest, subestimar fees/slippage, exceso de apalancamiento, señales de estafa en herramientas de terceros, etc.).
- Si algo que pido no tiene evidencia sólida de que funcione, quiero que me lo digan directamente en vez de complacerme.

## Objetivo del sistema
Agente de trading autónomo que usa un LLM como "cerebro" de decisión, con una capa de reglas de riesgo en **código determinístico** (no controlada por el LLM) que aplica límites de pérdida fijos y no negociables. Primero backtesting con datos históricos, después paper trading (simulación en tiempo real sin capital real), y recién si los resultados son consistentes en el tiempo, evaluar capital real chico — siempre revisando juntos los resultados antes de dar ese paso.

## Parámetros de riesgo definidos (no cambiar sin discutirlo)
- Capital hipotético de partida: **$10,000**
- Drawdown máximo absoluto (freno total del sistema, medido desde el pico más alto de capital, monto fijo no porcentual): **$2,000**
- Límite de pérdida diaria (se resetea cada día, frena el trading solo por ese día): **$200**
- Stop-loss por operación individual: **pendiente de definir** (se había sugerido un rango de $25-50 por operación, sujeto a confirmación explícita conmigo)
- Todos los límites de riesgo deben vivir en código determinístico, nunca delegados al criterio del LLM en tiempo de ejecución.

## Mercados y activos
- Operar en **cripto y forex en paralelo desde el inicio** (decisión explícita del usuario, aunque implica más complejidad de datos y ejecución).
- Cripto: solo monedas de valor / proyectos importantes (ej: Bitcoin, Ethereum, Chainlink, Uniswap, PancakeSwap, XRP). Nada de shitcoins ni proyectos especulativos de baja calidad.
- Forex: solo pares/activos sólidos, con trayectoria y fundamentos claros, evitando los de mayor margen de error.
- Sobre seguir a inversores institucionales (BlackRock, JP Morgan, etc.): los 13F son trimestrales y con hasta 45 días de retraso, no sirven como señal en tiempo real. Se acordó en su lugar usar **flujos de ETFs cripto spot** (ej. IBIT) como un filtro de contexto/sesgo direccional de bajo peso — nunca como señal principal ni gatillo de entrada — y sumar un **límite de correlación explícito en la capa de riesgo** para evitar sobre-concentración en activos correlacionados (esto ataca el riesgo de perder por un bajonazo sectorial completo).

## Arquitectura acordada (4 capas, en ciclo)
1. **Fuentes de datos**: precios cripto (vía API tipo ccxt/Binance) y forex, más indicadores técnicos (medias móviles, volumen, volatilidad) e indicadores de sentimiento de mercado amplio (dominancia BTC, funding rates, índice miedo/codicia) en vez de depender de un solo ETF.
2. **Decisión (LLM)**: recibe un resumen estructurado del mercado y propone comprar/vender/mantener con tamaño de posición sugerido. El LLM propone, no ejecuta directamente.
3. **Capa de riesgo (código)**: valida o bloquea la propuesta del LLM según los límites fijos definidos arriba. Es la red de seguridad; el LLM no la controla.
4. **Ejecución / simulación**: por ahora simula sobre datos históricos (backtest) o precios en vivo sin plata real (paper trading). No manda órdenes reales todavía.

## Plan de etapas (seguir en orden, sin saltar)
1. ✅ Definir parámetros de riesgo base (hecho, ver arriba — falta solo el stop-loss por operación)
2. ✅ Diseñar arquitectura de 4 capas (hecho, ver arriba)
3. ⬜ Armar entorno de backtesting con datos históricos
4. ⬜ Diseñar el prompt/estructura de decisión que recibe el LLM en cada ciclo
5. ⬜ Correr backtests, iterar sobre resultados, explicando cada métrica la primera vez que aparece
6. ⬜ Pasar a paper trading (simulación en tiempo real)
7. ⬜ Evaluar juntos, con criterios explícitos, si y cuándo pasar a capital real

## Decisiones técnicas ya tomadas
- Lenguaje: **Python** (por ser el estándar en trading cuantitativo, con librerías como pandas, ccxt, backtrader/vectorbt).
- Entorno de trabajo: Claude Code Desktop, apuntando a la carpeta `C:\Users\matia\OneDrive\Documents\Trading Agent`.

## Restricciones (nunca romper)
- Nunca sugerir pasar a capital real sin revisar juntos los resultados de backtesting y paper trading.
- Nunca presentar una plataforma, bot o servicio de terceros que prometa retornos garantizados o "sin esfuerzo" — marcarlo como red flag si aparece.
- La lógica de stop-loss / tolerancia a la baja debe vivir siempre en código determinístico.
- Explicar conceptos técnicos y financieros la primera vez que aparecen, en lenguaje simple.
- Si algo pedido no tiene evidencia sólida de que funcione, decirlo directamente.

## Riesgos ya señalados para tener en cuenta durante el desarrollo
Sobreoptimización de backtest (overfitting) — separar datos in-sample / out-of-sample. Subestimar fees, spread y slippage — modelarlos explícitamente. Doble superficie de error por operar cripto + forex en paralelo desde el día 1. El LLM no es determinístico — por eso el riesgo vive en código aparte. Paper trading no es capital real sin plata — es necesario pero no suficiente. Costo de tokens por ciclo de decisión frecuente. Estafas y plataformas de terceros con promesas irreales. Necesidad de testear el backtest en varios regímenes de mercado (alcista, bajista, lateral), no solo el período más favorable.
