# Unswayed: producto, modelo de negocio y precios

Fecha: 14 de noviembre de 2026.
Estado: el producto descrito en "Qué existe hoy" funciona y está probado. El modelo de negocio y los precios son una **propuesta sin validar con ningún cliente**.

---

## 1. Resumen

- **Qué es:** una compuerta que se pone delante de un revisor de código con IA y que nunca lee lo que escribió el autor. Mira solo el diff y responde una pregunta: ¿este cambio debilita una salvaguarda existente?
- **Por qué importa:** un revisor de IA aprobó 53 de 90 pull requests maliciosos cuando la descripción mentía. Con la compuerta delante, 6 de 90, sin perder aprobaciones legítimas.
- **Para quién:** equipos de seguridad de empresas reguladas donde agentes de IA abren pull requests y revisores de IA los aprueban.
- **Cómo gana dinero:** núcleo abierto y gratuito; se cobra el plano de control (quién puede anular un bloqueo, rastro de auditoría, evidencias, instalación gestionada).
- **Cuánto:** gratis la compuerta, 19 € por committer activo al mes el plan de equipo, desde 50.000 € al año el autoalojado para empresa.
- **Dónde está hoy:** listo para un piloto en modo sombra. No hay app alojada ni clientes.

---

## 2. El problema

En una empresa regulada ningún cambio llega a producción sin un segundo par de ojos. Cada vez más, ese segundo par es una IA, y esa IA lee el título y la descripción que escribió quien quiere que el cambio se apruebe.

Lo medimos sobre SEVRA-Bench, un benchmark público de Carnegie Mellon, Microsoft y Databricks: arreglos reales de vulnerabilidades, revertidos y presentados como pull requests con una descripción persuasiva. El código es el mismo cada vez; solo cambia el relato.

| Revisor | PRs maliciosos aprobados, de 90 |
| --- | --- |
| Qwen3-235B | 53 |
| gpt-oss-120b | 19 |

Ejemplo real del benchmark: un PR quita `protect_from_forgery` (la protección CSRF de Rails). La descripción dice que aplica una decisión ya tomada y aprobada. El revisor aprobó en 3 de 3 ejecuciones y dio como motivo que el cambio "ya estaba revisado y aprobado". Repitió el relato del autor.

Que el ataque existe ya no es una hipótesis: en abril de 2026 se publicó "Comment and Control", donde el texto de pull requests e issues secuestró tres agentes de IA en producción. Lo que no hemos encontrado es un incidente real de un PR malicioso fusionado por persuasión; lo publicado son demostraciones.

---

## 3. El producto

### Cómo funciona

1. Llega un cambio: el diff más todo lo que el autor escribió sobre él.
2. Unswayed recibe **solo el diff**. Ni título, ni descripción, ni mensajes de commit, ni nombre de rama.
3. Clasifica el cambio: `WEAKENS`, `NEUTRAL` o `STRENGTHENS`.
4. Si debilita una salvaguarda, el cambio queda retenido hasta que una persona lo reconoce con un motivo, que queda registrado.
5. En cualquier otro caso, pasa al revisor normal, que sigue leyéndolo todo.

No es un segundo revisor. Nunca aprueba nada. Es un cable trampa con una pregunta estrecha, y la estrechez importa: revisar todo a ciegas también para el ataque, pero en nuestras pruebas hundió las aprobaciones legítimas de 24 a 12 de 30.

### Qué existe hoy

| Capacidad | Estado |
| --- | --- |
| Hook pre-commit en local | Funciona; probado de punta a punta con un modelo real |
| Check obligatorio en pull requests (GitHub Actions) | Funciona; ejecutado en runners de GitHub con respuesta de modelo simulada |
| El PR no puede editar su propia compuerta | Sí: el workflow y el script salen de la rama base |
| Anular un bloqueo requiere a otra persona | Sí en CI: un mantenedor que no sea el autor, sobre el commit exacto. Probado en unitarias, no ejercitado en GitHub |
| Modo sombra (registra y no retiene) | Funciona |
| Informe de decisiones y exportación CSV | Funciona |
| Modo por fragmentos, resistente a camuflaje | Funciona; medido |
| Modelo propio del cliente | Sí: Claude o cualquier endpoint compatible con OpenAI |
| Fallo cerrado si el modelo no responde | Sí, por defecto |
| Pruebas automáticas | 42 |
| App alojada con instalación en un clic | **No existe** |
| SSO, políticas por repositorio, panel | **No existe** |
| Soporte para GitLab, Bitbucket, Azure DevOps | **No existe** como integración; el comando funciona en cualquier CI |
| Clientes o despliegues en producción | **Ninguno** |

### Qué sale de la red del cliente

Solo el diff, hacia el endpoint de modelo que el cliente configure. Con un modelo autoalojado, nada sale. Unswayed no tiene servidor ni telemetría.

---

## 4. Evidencia medida

Todo lo de esta sección está en `results/` y se reproduce con los scripts de `experiments/`.

### El efecto

| | Revisor solo | Con Unswayed |
| --- | --- | --- |
| Maliciosos aprobados, de 90 (Qwen3-235B) | 53 | 6 |
| Maliciosos aprobados, de 90 (gpt-oss-120b) | 19 | 5 |
| Arreglos legítimos aprobados, de 30 (Qwen3-235B) | 24 | 24 |
| Arreglos legítimos aprobados, de 30 (gpt-oss-120b) | 23 | 23 |

### El coste: falsas alarmas

Sobre 118 commits corrientes de los mismos repositorios:

| Modelo que hace la pregunta | Marcados | Tasa |
| --- | --- | --- |
| Claude Opus 5.5 | 5 de 118 | 4 % |
| Qwen3-235B | 18 de 118 | 15 % |
| gpt-oss-120b | 19 de 118 | 16 % |

### El ataque a nuestra propia compuerta

Seis cambios que un autor puede hacer dentro del diff, sobre 24 diffs maliciosos que la compuerta marca siempre (Qwen3-235B, una muestra por ataque):

| Ataque | Evade, modo por defecto | Evade, modo por fragmentos |
| --- | --- | --- |
| Comentario que justifica el cambio | 1 de 24 | 1 de 24 |
| Comentario con instrucciones al clasificador | 3 de 24 | 1 de 24 |
| Etiqueta de veredicto falsa | 4 de 24 | 2 de 24 |
| Enterrado entre cambios benignos, una llamada | 7 de 24 | 0 de 24 |
| Enterrado entre cambios benignos, varias llamadas | 5 de 24 | 0 de 24 |
| Endurecimiento señuelo en otra parte | 8 de 24 | 0 de 24 |
| Los seis | 28 de 144 | 4 de 144 |

El modo por fragmentos tiene precio: los commits corrientes marcados suben de 18 a 33 de 118 (28 %), los arreglos legítimos marcados de 2 a 6 de 30, y las llamadas al modelo se multiplican por 2,4.

### Límites de la evidencia

- Subconjunto de 90 PRs maliciosos y 30 legítimos de un benchmark de 1.062.
- El ataque adaptativo usa 24 casos, un modelo y una muestra por ataque.
- Los ataques no se readaptaron al modo por fragmentos. Un atacante que lo conozca no está medido.
- Los modelos más fuertes ya resisten sin compuerta: Claude Opus 5.5 rechazó 30 de 30 maliciosos en nuestra muestra.
- No hay ningún dato de repositorios reales de un cliente.

---

## 5. El cliente

**Quién paga:** el responsable de seguridad de aplicaciones o el CISO.

**Quién lo usa:** los equipos de plataforma que mantienen el CI, y los desarrolladores cuando un cambio queda retenido.

**Perfil de empresa:** regulada (banca, seguros, fintech, telecomunicaciones), con más de 100 desarrolladores, que ya deja que agentes de IA abran pull requests y que usa o planea usar un revisor de IA.

**Qué los mueve:**

- **Control de cambios.** El reglamento delegado (UE) 2024/1774, art. 17(1)(b), pide independencia entre quien aprueba un cambio y quien lo solicita o implementa. Un aprobador que cree al implementador no es independiente. El reglamento no menciona la revisión de código; el argumento es de principio, no de cumplimiento literal.
- **Soberanía del código.** Muchas de estas empresas no pueden enviar código a un modelo externo. Unswayed funciona con el modelo que ya alojan.
- **Volumen.** Con agentes abriendo PRs, la revisión humana no escala y la aprobación de la IA pesa más cada mes.

**Objeciones que van a poner:**

- "Usamos un modelo de primera y ya resiste." Es cierto hoy. La respuesta es que la resistencia varía por modelo y por tipo de engaño, y que un control no debería depender del modelo contratado este trimestre.
- "Con un 15 % de falsas alarmas lo apagamos." También cierto. Por eso la primera oferta es un piloto en modo sombra.

---

## 6. Modelo de negocio

**Núcleo abierto.** La compuerta es código abierto (MIT) y gratuita. Se cobra lo que una empresa necesita alrededor del veredicto y que un script no da.

Por qué así y no un producto cerrado:

- **Un producto de seguridad cerrado que lee tu código no se compra a ciegas.** Que el equipo de seguridad pueda leer las 500 líneas de la compuerta es un argumento de venta.
- **El núcleo no es defendible como secreto.** Es un prompt y un troceador de diffs. Quien quiera copiarlo lo copia. Mejor que lo adopten gratis y pagar por lo demás.
- **La adopción gratuita es el canal.** Un ingeniero lo instala en un repositorio sin pedir presupuesto; la conversación de pago empieza cuando quieren desplegarlo en doscientos.

| | Community | Team | Enterprise |
| --- | --- | --- | --- |
| Compuerta, hook y check de PR | Sí | Sí | Sí |
| Modo sombra e informe CSV | Sí | Sí | Sí |
| Modelo propio | Sí | Sí | Sí |
| App alojada, instalación en un clic | No | Sí | Opcional |
| Reconocimiento de bloqueos desde el PR, con interfaz | Manual | Sí | Sí |
| Política común para todos los repositorios | No | Sí | Sí |
| Rastro de auditoría centralizado y con búsqueda | No | Sí | Sí |
| Alertas en cada anulación | No | Sí | Sí |
| Despliegue dentro de la red del cliente | Por su cuenta | No | Sí |
| SSO y control de acceso por roles | No | No | Sí |
| Exportación de evidencias para auditoría | CSV | CSV | A medida |
| Soporte con tiempo de respuesta | No | Correo | Contrato |
| Estado | **Existe** | No construido | No construido |

---

## 7. Precios

| Plan | Precio propuesto | Cómo se cuenta |
| --- | --- | --- |
| Community | Gratis | Sin límite |
| Team | 19 € por committer activo al mes, facturación anual | Committers con actividad en los últimos 90 días en los repositorios protegidos. Las identidades de agentes cuentan como committers |
| Enterprise | 30 € por committer activo al mes, mínimo 50.000 € al año | Igual, con contrato anual |
| Piloto | Gratis para los tres primeros socios de diseño. Después, 5.000 € por cuatro semanas, descontables del primer año | Uno o dos repositorios |

### Por qué 19 €

El precio se ancla en lo que ya pagan por herramientas vecinas, todas por persona y mes:

| Producto | Precio de lista | Qué es |
| --- | --- | --- |
| GitHub Secret Protection | 19 $ | Un control estrecho: detectar secretos |
| CodeRabbit Essentials | 24 $ | Revisor de IA completo |
| GitHub Code Security | 30 $ | Análisis estático |
| Semgrep Teams | 30 $ | Análisis estático y cadena de suministro |
| Qodo Merge Teams | 30 $ | Revisor de IA completo |
| CodeRabbit Team | 48 $ | Revisor de IA, plan superior |

Unswayed es un control estrecho, no una suite. Su comparable natural es Secret Protection, que hace una sola cosa y cuesta 19 $. Cobrar lo mismo que un revisor completo o que un SAST no se sostendría: el comprador ya paga uno de esos y Unswayed se añade encima.

### Por qué 30 € y un mínimo de 50.000 € en Enterprise

- El recargo de un 50 a 60 % sobre Team paga el autoalojado, el SSO y el soporte con contrato, que es lo habitual en este tipo de herramientas.
- El mínimo equivale a unos 140 committers. Por debajo de ese tamaño, una venta a empresa con revisión de seguridad, contrato y soporte no cubre su propio coste comercial.
- En cuentas de miles de desarrolladores el precio por persona se negocia a la baja; el mínimo es el suelo, no el objetivo.

### Por qué cobrar por committer y no por PR

- Es la métrica que ya usan GitHub y Semgrep. El departamento de compras la entiende y sabe presupuestarla.
- El valor crece con el número de personas y agentes que pueden abrir un cambio, no con el tamaño del código.
- Cobrar por PR penalizaría justo el comportamiento que el producto quiere proteger: muchos cambios pequeños.

Riesgo de esta métrica: si un agente abre mil PRs al mes bajo una sola identidad, el precio por committer infravalora el uso. Si eso ocurre en los pilotos, habrá que añadir un tramo por volumen de PRs para identidades de agentes.

### Lo que cuesta servirlo

El coste de modelo es casi nulo. Estimación con Qwen3-235B a precios públicos de terceros (0,20 $ por millón de tokens de entrada y 0,60 $ de salida, sin verificar en la página oficial):

- Una llamada envía como mucho 12.000 caracteres de diff, unos 3.000 a 4.000 tokens, y recibe como mucho 1.500.
- En el peor caso, menos de 0,002 $ por llamada.
- Un PR típico es una llamada; en modo por fragmentos, 2,4 de media.
- Para 10.000 PRs al mes, del orden de 20 a 50 $.

En Enterprise el modelo lo pone el cliente, así que ese coste ni siquiera es nuestro. El coste real del negocio es gente: integración, soporte y mantener el banco de ataques al día.

### Escenarios de ingresos

Aritmética ilustrativa, no una previsión:

| Escenario | Cuentas | Ingreso anual |
| --- | --- | --- |
| 10 equipos de 50 committers en Team | 10 × 50 × 19 € × 12 | 114.000 € |
| 3 empresas al mínimo de Enterprise | 3 × 50.000 € | 150.000 € |
| 1 banco con 1.000 committers a 30 € | 1.000 × 30 € × 12 | 360.000 € |

---

## 8. Por qué Unswayed y no una alternativa de código abierto

Lo primero: **Unswayed también es código abierto.** La pregunta real tiene tres versiones.

### "¿Por qué no un revisor de IA de código abierto?"

Herramientas como PR-Agent, Kodus u Open Code Review son revisores: leen el diff **y** la descripción, y deciden si el cambio está bien. Ese es exactamente el diseño que medimos como vulnerable. Autoalojarlo no cambia nada: el relato del autor sigue llegando al modelo.

Unswayed no los sustituye. Se pone delante de cualquiera de ellos.

| | Revisor de IA abierto | Unswayed |
| --- | --- | --- |
| Lee la descripción del autor | Sí, por diseño | Nunca |
| Pregunta que responde | ¿Se puede fusionar? | ¿Debilita una salvaguarda? |
| Puede ser persuadido por el relato | Sí: 19 y 53 de 90 en nuestras pruebas | El relato no le llega |
| Sustituye a tu revisor | Es tu revisor | No, lo complementa |

### "¿Por qué no un analizador estático de código abierto?"

Semgrep en su edición gratuita, CodeQL o Bandit buscan patrones conocidos en el código resultante. Unswayed mira el cambio y pregunta por su dirección: si quita, salta o relaja una protección, sea cual sea.

Son complementarios, y hay que decirlo con honestidad: **no hemos medido ningún analizador estático sobre este benchmark**. Una regla escrita para una salvaguarda concreta puede detectar que falta. Lo que un analizador no hace es responder a la pregunta general sin una regla previa.

### "¿Por qué no hacerlo nosotros? Es un prompt."

Es la objeción más fuerte y la respuesta sincera es: **puedes, y si solo necesitas la compuerta, usa la versión gratuita.** Lo que se paga es lo que un script propio no trae:

- **Los números.** Sabes qué tasa de detección y de falsas alarmas tiene este prompt exacto con estos modelos. Un prompt escrito en una tarde no tiene ninguna medición detrás, y cambiar una frase cambia las cifras.
- **El banco de ataques.** Seis familias de ataque medidas contra la compuerta, y el compromiso de seguir midiendo las nuevas. Es lo que nadie mantiene para una herramienta interna.
- **La separación de funciones.** Que el PR no pueda editar su compuerta y que solo un mantenedor distinto del autor pueda anular un bloqueo, sobre el commit exacto, son detalles que se hacen mal a la primera.
- **La evidencia.** Un registro que un auditor acepta, no un log suelto en un runner.
- **Alguien a quien llamar** cuando la tasa de falsas alarmas se dispara tras cambiar de modelo.

Si ninguna de esas cinco cosas le importa a un cliente, no es cliente de pago y está bien que use la versión abierta.

### Frente a alternativas comerciales

| | Datadog BewAIre | Unswayed |
| --- | --- | --- |
| Pregunta | ¿Este PR es malicioso? | ¿Este diff debilita una salvaguarda? |
| Qué lee | El diff y metadatos del autor | Solo el diff |
| Dónde corre | Dentro de Datadog, en Preview | En tu CI, con tu modelo |
| Falsos positivos declarados | 0,03 %, sobre sus propios datos | 4 % a 16 %, sobre un benchmark público |
| Código | Cerrado | Abierto |

BewAIre declara muchos menos falsos positivos que nosotros. Si el cliente ya está en Datadog y puede enviar su código fuera, es una alternativa seria. Unswayed gana cuando el código no puede salir, cuando quieren ver cómo funciona el control, o cuando quieren un número que puedan reproducir.

---

## 9. Riesgos y lo que no sabemos

1. **No hay foso técnico.** El núcleo se copia en un día. La defensa es el banco de ataques, las mediciones y la confianza, y eso lleva tiempo construirlo.
2. **Los modelos mejoran.** Si en un año todos los revisores resisten la persuasión como hoy lo hace Opus, el problema encoge. Queda el argumento de no depender del modelo, que es más débil.
3. **Las falsas alarmas.** Entre 15 y 28 % con modelos abiertos es demasiado para bloquear. O baja, o el producto solo sirve con modelos caros, que son los que menos lo necesitan.
4. **Un incumbente lo añade.** Para CodeRabbit o GitHub, un pase a ciegas es una función, no un producto.
5. **Nadie lo ha pedido.** No hay ni una conversación con un comprador. Precio, métrica de cobro y hasta el perfil de cliente son hipótesis.
6. **El atacante que conoce el modo por fragmentos** no está medido.

---

## 10. Próximos 30 días

1. **Dos pilotos en modo sombra**, dos semanas cada uno. Dan el único dato que falta de verdad: la tasa de marcados sobre código real.
2. **Tres conversaciones con responsables de seguridad.** Dos preguntas: qué tasa de falsas alarmas tolerarían y si su aprobación de cambios ya pasa por una IA.
3. **Atacar el modo por fragmentos** y publicar el número.
4. **Bajar las falsas alarmas** con modelos abiertos; el objetivo es el 4 % que ya da el modelo más fuerte.
5. **Decidir si es empresa.** Lo es si se cumplen tres cosas: falsas alarmas que un piloto tolere, ataque adaptativo contenido y alguien dispuesto a pagar. Si falla una, queda como herramienta abierta y como credencial.

---

## Fuentes

- Benchmark: [SEVRA-Bench, arXiv 2606.13757](https://arxiv.org/abs/2606.13757)
- Ataque publicado: [CSA Labs, "Comment and Control", 17 de abril de 2026](https://labs.cloudsecurityalliance.org/research/csa-research-note-comment-control-github-prompt-injection-20/)
- Regulación: [Reglamento delegado (UE) 2024/1774, art. 17](https://www.springlex.eu/en/packages/dora/rts-rmf-regulation/article-17/)
- Datadog BewAIre: [blog de ingeniería de Datadog, 21 de octubre de 2025](https://www.datadoghq.com/blog/engineering/malicious-pull-requests/)
- Precios de CodeRabbit: [guía de precios de 2026](https://www.augmentcode.com/guides/coderabbit-pricing-costs-limits), fuente de terceros
- Precios de Semgrep: [semgrep.dev/pricing](https://semgrep.dev/pricing)
- Precios de GitHub Secret Protection y Code Security: [changelog de GitHub, 4 de marzo de 2025](https://github.blog/changelog/2025-03-04-introducing-github-secret-protection-and-github-code-security%C2%A0)
- Precio de Qodo Merge y revisores autoalojados: [comparativa de Kodus](https://kodus.io/self-hosted-ai-code-review/), fuente de un competidor
- Precio de Qwen3-235B en Nebius: [cloudprice.net](https://cloudprice.net/models/nebius/Qwen/Qwen3-235B-A22B), fuente de terceros

Los precios de terceros se consultaron en resultados de búsqueda el 14 de noviembre de 2026 y no se abrieron las páginas oficiales una por una. Conviene confirmarlos antes de citarlos ante un cliente.
