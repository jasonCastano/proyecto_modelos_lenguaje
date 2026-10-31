export function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div>
          <p className="section-label">RAG Ingenio Manuelita</p>
          <h2>Una memoria pública, con la fuente a la vista.</h2>
          <p>
            Proyecto académico de la Maestría en IA y Ciencia de Datos de la Universidad Autónoma
            de Occidente.
          </p>
        </div>
        <div className="footer-links">
          <a href="#consola">Preguntar al corpus</a>
          <a href="#modulo-1">Recorrer el Módulo 1</a>
          <a href="https://github.com/jasonCastano/proyecto_modelos_lenguaje">Repositorio</a>
          <a href="https://github.com/jasonCastano/proyecto_modelos_lenguaje/blob/main/docs/arquitectura.html">Arquitectura</a>
          <a href="https://www.manuelita.com/">Sitio oficial de Manuelita</a>
        </div>
        <p className="footer-legal">
          No afiliado oficialmente a Grupo Manuelita. Contenido de terceros atribuido a sus fuentes.
          Proyecto académico 2026.
        </p>
      </div>
    </footer>
  );
}
