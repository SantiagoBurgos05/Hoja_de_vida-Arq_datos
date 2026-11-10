import React from "react";
import { Section, Select, Text } from "../components/ui.jsx";
import { getPath, setPath } from "../lib/format.js";

export default function Personal({ resume, setResume }) {
  const t = (path, label, extra = {}) => <Text label={label} value={getPath(resume.personal, path)} onChange={(v) => setResume((r) => ({ ...r, personal: setPath(r.personal, path, v) }))} {...extra} />;
  const s = (path, label, options) => <Select label={label} value={getPath(resume.personal, path)} options={options} onChange={(v) => setResume((r) => ({ ...r, personal: setPath(r.personal, path, v) }))} />;
  return (
    <Section n="1" title="Datos personales">
      <div className="grid">
        {t("primer_apellido", "Primer apellido", { maxLength: 60 })}
        {t("segundo_apellido", "Segundo apellido (o de casada)", { maxLength: 60 })}
        {t("nombres", "Nombres", { maxLength: 80 })}
        {s("tipo_documento", "Documento de identificación", [["CC", "C.C."], ["CE", "C.E."], ["PAS", "Pasaporte"]])}
        {t("numero_documento", "Número", { maxLength: 30 })}
        {s("sexo", "Sexo", [["F", "F"], ["M", "M"]])}
        {s("nacionalidad", "Nacionalidad", [["COL", "Colombiana"], ["EXTRANJERO", "Extranjero"]])}
        {t("pais_nacionalidad", "País (si es extranjero)")}
        {s("libreta_militar.clase", "Libreta militar", [["primera", "Primera clase"], ["segunda", "Segunda clase"]])}
        {t("libreta_militar.numero", "Número de libreta")}
        {t("libreta_militar.dm", "D.M.")}
      </div>
      <h3>Fecha y lugar de nacimiento</h3>
      <div className="grid">
        {t("nacimiento.fecha", "Fecha", { type: "date" })}
        {t("nacimiento.pais", "País")}{t("nacimiento.departamento", "Departamento")}{t("nacimiento.municipio", "Municipio")}
      </div>
      <h3>Dirección de correspondencia</h3>
      <div className="grid">
        {t("correspondencia.direccion", "Dirección", { wide: true })}
        {t("correspondencia.pais", "País")}{t("correspondencia.departamento", "Departamento")}{t("correspondencia.municipio", "Municipio")}
        {t("correspondencia.telefono", "Teléfono")}{t("correspondencia.email", "Correo electrónico", { type: "email" })}
      </div>
    </Section>
  );
}
