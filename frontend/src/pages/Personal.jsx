import React from "react";
import { Card, RequiredLegend, Select, Text } from "../components/ui.jsx";
import { getPath, setPath } from "../lib/format.js";

export default function Personal({ resume, setResume }) {
  const set = (path, v) => setResume((r) => ({ ...r, personal: setPath(r.personal, path, v) }));
  const t = (path, label, extra = {}) => <Text label={label} value={getPath(resume.personal, path)} onChange={(v) => set(path, v)} {...extra} />;
  const s = (path, label, options, extra = {}) => <Select label={label} value={getPath(resume.personal, path)} options={options} onChange={(v) => set(path, v)} {...extra} />;
  const extranjero = getPath(resume.personal, "nacionalidad") === "EXTRANJERO";

  return (
    <div className="stack">
      <Card icon="id" title="Identificación" desc="Tal como aparece en su documento de identidad.">
        <RequiredLegend />
        <div className="grid">
          {t("primer_apellido", "Primer apellido", { maxLength: 60, autoComplete: "family-name", required: true })}
          {t("segundo_apellido", "Segundo apellido (o de casada)", { maxLength: 60 })}
          {t("nombres", "Nombres", { maxLength: 80, autoComplete: "given-name", required: true })}
        </div>
        <div className="grid">
          {s("tipo_documento", "Documento de identificación", [["CC", "Cédula de ciudadanía (C.C.)"], ["CE", "Cédula de extranjería (C.E.)"], ["PAS", "Pasaporte"]])}
          {t("numero_documento", "Número", { maxLength: 30, inputMode: "numeric", required: true })}
          {s("sexo", "Sexo", [["F", "Femenino (F)"], ["M", "Masculino (M)"]])}
        </div>
        <div className="grid">
          {s("nacionalidad", "Nacionalidad", [["COL", "Colombiana"], ["EXTRANJERO", "Extranjero"]])}
          {t("pais_nacionalidad", "País (si es extranjero)", { hint: extranjero ? "Indique el país de su nacionalidad." : "Solo si su nacionalidad es extranjera." })}
        </div>
      </Card>

      <Card icon="shield" tone="accent" title="Libreta militar" desc="Opcional. Diligencie solo si aplica a su caso.">
        <div className="grid">
          {s("libreta_militar.clase", "Libreta militar", [["primera", "Primera clase"], ["segunda", "Segunda clase"]], { placeholder: "No aplica" })}
          {t("libreta_militar.numero", "Número de libreta")}
          {t("libreta_militar.dm", "D.M.", { hint: "Distrito militar" })}
        </div>
      </Card>

      <Card icon="calendar" tone="warn" title="Fecha y lugar de nacimiento">
        <div className="grid">
          {t("nacimiento.fecha", "Fecha", { type: "date", autoComplete: "bday" })}
          {t("nacimiento.pais", "País")}
          {t("nacimiento.departamento", "Departamento")}
          {t("nacimiento.municipio", "Municipio")}
        </div>
      </Card>

      <Card icon="map" title="Dirección de correspondencia" desc="Datos de contacto que aparecerán en el formato.">
        <div className="grid">
          {t("correspondencia.direccion", "Dirección", { wide: true, autoComplete: "street-address" })}
        </div>
        <div className="grid">
          {t("correspondencia.pais", "País", { autoComplete: "country-name" })}
          {t("correspondencia.departamento", "Departamento")}
          {t("correspondencia.municipio", "Municipio")}
        </div>
        <div className="grid">
          {t("correspondencia.telefono", "Teléfono", { type: "tel", autoComplete: "tel" })}
          {t("correspondencia.email", "Correo electrónico", { type: "email", autoComplete: "email" })}
        </div>
      </Card>
    </div>
  );
}
