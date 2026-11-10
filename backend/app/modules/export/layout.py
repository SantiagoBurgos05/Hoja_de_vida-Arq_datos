"""Coordenadas (puntos PDF, origen arriba-izquierda; se convierte a reportlab al dibujar)
medidas sobre la plantilla oficial `fuhv_persona_natural.pdf` (612x792 pt, 3 páginas).
Medidas con pdfplumber (posición de rótulos) y verificadas visualmente (ver docs/estado.md)."""

H = 792.0

# ---- Página 1: datos personales ------------------------------------------------
P1_TEXT = {  # (x, baseline_top, ancho_máx)
    "primer_apellido": (64, 186, 155), "segundo_apellido": (229, 186, 160), "nombres": (399, 186, 165),
    "numero_documento": (185, 218, 105), "pais_nacionalidad": (477, 218, 82),
    "libreta_numero": (338, 251, 116), "libreta_dm": (497, 251, 60),
    "nac_pais": (117, 302.5, 115), "nac_depto": (117, 320.5, 115), "nac_municipio": (117, 337.5, 115),
    "dir_direccion": (294, 284, 188),
    "dir_pais": (347, 302.5, 88), "dir_depto": (475, 302.5, 85), "dir_municipio": (347, 320.5, 210),
    "dir_telefono": (347, 337.5, 88), "dir_email": (474, 337.5, 87),
}
P1_MARKS = {  # centro (x, y_top) de círculos
    ("tipo_documento", "CC"): (85.6, 215), ("tipo_documento", "CE"): (116.9, 215), ("tipo_documento", "PAS"): (150, 215),
    ("sexo", "F"): (320, 215), ("sexo", "M"): (345, 215),
    ("nacionalidad", "COL"): (387.5, 214.5), ("nacionalidad", "EXTRANJERO"): (460, 214.5),
    ("libreta", "primera"): (148.7, 246), ("libreta", "segunda"): (264, 244.5),
}
P1_DATE = {"dia": (144, 285.5), "mes": (194, 285.5), "anio": (254, 285.5)}  # centro x, baseline

GRADE_X = {1: 106.3, 2: 122.8, 3: 140.3, 4: 157.4, 5: 173.8, 6: 191, 7: 208, 8: 225, 9: 242, 10: 259, 11: 276}
GRADE_Y = 471.5
TITULO_BASICA = (362, 441.5, 160)
GRADO_MES = (359, 472.5)
GRADO_ANIO = (429, 472.5)

EDU_ROW_TOP = [579.0, 596.5, 614.0, 631.5, 648.5]
EDU_ROW_BASE = 11.5
EDU = {"modalidad": (84, "c"), "semestres": (142, "c"), "si": (187, "c"), "no": (211, "c"),
       "nombre": (226, "l", 194), "mes": (435.5, "c"), "anio": (474, "c"), "tarjeta": (504, "l", 63)}
EDU_MAX_ROWS = 5

LANG_ROW_BASE = [720.5, 736.5]
LANG_NAME = (157, 140)
LANG_COLS = {"habla": {"R": 306.6, "B": 323.5, "MB": 340.5}, "lee": {"R": 357.7, "B": 374.5, "MB": 391.5},
             "escribe": {"R": 408.6, "B": 425.5, "MB": 442.5}}
LANG_MAX_ROWS = 2

# ---- Página 2: experiencia laboral (4 bloques) ---------------------------------
EXP_BLOCK_TOP = [219.6, 350.2, 479.8, 610.2]   # parte superior del rótulo «EMPRESA O ENTIDAD» de cada bloque
EXP_MAX = 4
# offsets respecto al top del bloque
EXP = {"empresa": (62, 20, 255), "publica": (347, 20), "privada": (394, 20), "pais": (425, 20, 140),
       "departamento": (62, 50, 170), "municipio": (241, 50, 165), "correo": (417, 50, 148),
       "telefonos": (62, 80, 170), "cargo": (62, 108, 175), "dependencia": (245, 108, 165), "direccion": (414, 108, 150)}
EXP_DATE_BASE = 80.5
EXP_DATE_X = {"ing_dia": 269, "ing_mes": 319, "ing_anio": 376, "ret_dia": 436, "ret_mes": 486, "ret_anio": 542.5}

# ---- Página 3: tiempo total ------------------------------------------------------
TIME_ROW_BASE = {"servidor_publico": 194.5, "empleado_privado": 222.5, "independiente": 250.5, "total": 278.5}
TIME_X = {"anios": 394, "meses": 464.5}

# Centros de las casillas de dígitos del AÑO (4 casillas) -- para no cruzar las divisiones
YEAR_CELLS = {"nacimiento": [239, 249, 259, 269], "grado": [414.4, 424.4, 434.4, 444.4], "edu": [454.3, 468, 481.5, 494.5],
              "ing": [361.25, 371.25, 381.25, 391.25], "ret": [527.5, 537.5, 547.5, 557.5]}
