/** Estado de los servicios (spec 026, FR-022): forma y texto, no solo color; razón y acción a la vista. */
import type { ServiceStatus } from "../../lib/types";

const STATUS_TEXT: Record<ServiceStatus["status"], string> = {
  up: "disponible",
  down: "caído",
  degraded: "con errores",
  unknown: "sin dato",
};

export function ServiceStatusBar({ services }: { services: ServiceStatus[] }) {
  return (
    <section aria-labelledby="services-title" className="services">
      <h2 className="panel-title" id="services-title">
        Servicios
      </h2>
      <ul className="services__list">
        {services.map((service) => (
          <li className="service" data-status={service.status} key={service.id}>
            <span aria-hidden="true" className="service__mark" />
            <span className="service__name">{service.label}</span>
            <span className="service__state">{STATUS_TEXT[service.status]}</span>
            <span className="service__reason">{service.reason}</span>
            {service.action ? <span className="service__action">Qué hacer: {service.action}</span> : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
