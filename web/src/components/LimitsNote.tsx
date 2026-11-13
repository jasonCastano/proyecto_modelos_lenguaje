export function LimitsNote() {
  return (
    <section className="limits" data-testid="limits-note" aria-labelledby="limits-title">
      <div className="limits-inner">
        <div>
          <p className="section-label">Lo que todavía falta</p>
          <h2 id="limits-title">Una demo honesta también dice sus límites.</h2>
        </div>
        <div>
          <p>
            El corpus cubre información pública y el sistema cita o declara vacíos; no es asesoría
            oficial de Manuelita. Del Módulo 1 faltan la evaluación real de las 40 preguntas y el
            ensayo de la demo. Del Módulo 2 faltan la calificación humana de las repreguntas, Qdrant
            con servidor dedicado (hoy corre embebido), el gatekeeper Jev y el despliegue; además,
            el agente supera los 10 s en el 6 % de las consultas.
          </p>
          <p>
            El contenido de terceros pertenece a sus fuentes. El proyecto es académico y no
            representa una afiliación oficial con la empresa.
          </p>
        </div>
      </div>
    </section>
  );
}
