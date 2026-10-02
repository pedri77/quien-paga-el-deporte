#!/usr/bin/env python3
"""¿Quién paga el deporte? — agrega las subvenciones públicas al deporte (BDNS 2024-2025).

    python3 scripts/deporte_build.py            # lee la sqlite de quien-cobra (solo lectura) y escribe data/

Entrada: la base `bdns.sqlite` construida por el episodio cci-09 (quien-cobra/scripts/bdns_build.py).
Sólo contiene concesiones a entidades jurídicas (las personas físicas se descartaron allí).

Método (ver data/informe.md):
1. La BDNS no tiene «Deporte» como finalidad (va dentro de «Cultura»), así que el deporte se
   identifica por el NOMBRE del beneficiario: federaciones, clubes, SAD, patronatos, empresas deportivas.
2. Señal secundaria: convocatorias cuyos sectores CNAE son EXCLUSIVAMENTE 93.1x (actividades deportivas).
   Añade beneficiarios de nombre no evidente (sobre todo ayuntamientos que reciben ayudas de diputaciones).
3. La precisión del clasificador se mide a mano sobre una muestra fija (VALIDACION) y se publica.

Determinista: misma sqlite -> mismos ficheros (sin marcas de tiempo, muestra con semilla fija).
"""
from __future__ import annotations

import json
import random
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB = ROOT.parent / "quien-cobra" / "work" / "bdns.sqlite"
YEARS = [2024, 2025]
FUENTE = ("BDNS – Sistema Nacional de Publicidad de Subvenciones y Ayudas Públicas (IGAE, Ministerio de Hacienda), "
          "vía descarga del episodio cci-09 «¿Quién cobra?»")
API = "https://www.infosubvenciones.es/bdnstrans/api/concesiones/busqueda"

# ------------------------------------------------------------------ clasificador por nombre
def norm(s: str | None) -> str:
    s = re.sub(r"&X[0-9A-F]{2}", "N", (s or "").upper())  # «MONTA&XD1A»: Ñ mal codificada en origen
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", s)).strip()


# Palabras por deporte. Las de AMBIGUAS sólo valen si el nombre tiene contexto deportivo
# (DEPORT*, FEDERACIÓN o CLUB): «VELA», «TIRO», «MOTOR», «CAZA» solas no identifican un club.
SPORT_RX = {
    "futbol": "FUTBOL|FOOTBAL|FUTBOL SALA|FUTSAL|FOOTBALL|FUTEBOL|FUTBOL CLUB|FC|CF|ATHLETIC CLUB|BALOMPIE|BALOMPEDICA|FUTBOLISTAS|FUTBOL 7|FUTBOL AMERICANO|FUTBOL PLAYA",
    "baloncesto": "BALONCESTO|BASQUET|BASKET|BASKETBALL|BALONCESTISTA|SASKIBALOI|BASQUETBOL|BALONCES|BALONCENTISTAS",
    "balonmano": "BALONMANO|BALOMNANO|HANDBOL|HANDBALL|ESKUBALOI|BALONMAN",
    "atletismo": "ATLETISMO|CORRECAMINOS|MARXA NORDICA|MARCHA NORDICA|ATLETISME|ATLETAS|ATLETES|CORREDORES|RUNNERS|RUNNING|MARATON|MARATHON|TRAIL|CROSS|ATLETISMOA|KORRIKALARI|MARCHA",
    "natacion": "NATACION|ACUATICO|ACUATIC|AQUATIC|NATACIO|IGERIKETA|WATERPOLO|NADADORES|SINCRONIZADA|NATACION SINCRONIZADA",
    "ciclismo": "CICLISTA|CICLISMO|CICLISME|BTT|BICI|BICICLETA|TXIRRINDULARI|TXIRRINDULARITZA|MTB|CICLOTURISTA|CICLOTURISMO|BIKE|BMX",
    "tenis": "TENIS|TENNIS",
    "padel": "PADEL",
    "voleibol": "VOLEIBOL|VOLEYPLAYA|VOLEY PLAYA|VOLEI|VOLLEY|VOLEY|VOLLEYBALL|BOLEIBOL",
    "rugby": "RUGBY|RUGBI",
    "hockey": "HOCKEY|HOQUEI|UNIHOCKEY|FLOORBALL",
    "patinaje": "PATIN|PATINAJE|PATINATGE|PATINES|ROLLER|SKATE|SKATEBOARD|PATINAXE",
    "gimnasia": "GIMNASIA|ACROBACIA|GIMNASTICA|GIMNASTIC|RITMICA|GIMNASTICO|AEROBIC|TRAMPOLIN|GIMNASTIKA|ACROBATICA",
    "artes_marciales": "JUDO|VOVINAM|VIET VO DAO|KARATE|TAEKWONDO|TAEKWON DO|KUNG FU|AIKIDO|JIU JITSU|JUJUTSU|JIUJITSU|KICK BOXING|KICKBOXING|MUAY THAI|WUSHU|ARTES MARCIALES|ARTS MARCIALS|KENDO|KRAV MAGA|HAPKIDO|FULL CONTACT|MMA|CAPOEIRA|TAI CHI|TAICHI|SAMBO|KARATE DO|YUDO",
    "boxeo": "BOXEO|BOXING|BOXEIG|BOXA|BOXEADORES",
    "esgrima": "ESGRIMA",
    "remo_piraguismo": "REMO|PIRAGUISMO|PIRAGUA|PIRAGUISME|KAYAK|CANOA|TRAINERAS|TRAINERA|ARRAUN|ARRAUNKETA|BATELES|REM|CANOTAJE",
    "vela_nautica": "VELA|NAUTICO|NAUTIC|NAUTICA|MARITIMO|MOTONAUTICA|WINDSURF|SURF|SURFING|KITESURF|KITE|BUCEO|SUBACUATICAS|SUBMARINISMO|ESQUI NAUTICO|REGATAS|REGATA|SALVAMENTO|SOCORRISMO|SALVAMENT|PESCA SUBMARINA|PADDLE SURF|VELA LATINA",
    "golf": "GOLF|PITCH AND PUTT",
    "hipica": "HIPICA|HIPICO|ECUESTRE|EQUITACION|HIPIKA|DOMA|POLO|CABALLO|CABALLOS|ENGANCHES|RAID",
    "montana_escalada": "MONTANA|MONTANISMO|MUNTANYA|MUNTANYISME|MENDI|MENDIZALE|MENDIZALEAK|ALPINO|ALPINISMO|ESCALADA|SENDERISMO|EXCURSIONISTA|EXCURSIONISMO|MONTANEROS|ESPELEOLOGIA|ESPELEO|MONTANEIROS|ESCALADORES|SENDERISTAS|TREKKING|ANDARINES|CAMINANTES",
    "esqui_invierno": "ESQUI|SKI|HIELO|CURLING|SNOWBOARD|DEPORTES DE INVIERNO|ESPORTS D HIVERN|ESQUI DE FONDO|ESKI|GELO|GEL",
    "triatlon": "TRIATLON|TRIATLO|DUATLON|TRIATLETAS",
    "ajedrez": "AJEDREZ|ESCACS|XADREZ|XAKE|AJEDRECISTICO|AJEDRECISTAS",
    "petanca_bolos": "PETANCA|PETANCO|BOLOS|BOLO|BIRLES|BOLEROS|BOLERAS|BOWLING|BITLLES|BOLERA|BOLO CELTA|BOLA|BOLOS CELTAS|BOLOS LEONESES",
    "pelota": "PELOTA|CESTA PUNTA|PILOTA|PELOTA VASCA|PELOTARI|PELOTAZALE|FRONTENIS|FRONTON|PILOTAZALE|PALETA|PILOTARI|PELOTA MANO",
    "tiro": "TIRO|TIRO OLIMPICO|TIRO CON ARCO|ARQUEROS|ARCO|TIRO AL PLATO|ARQUERS|TIR|TIRADORES|ARKU",
    "motor": "MOTOCICLISMO|AUTOMOVILISMO|MOTOR|MOTO|MOTOS|MOTOCLUB|MOTO CLUB|KARTING|RALLY|RALLYE|TRIAL|ENDURO|MOTORSPORT|ESCUDERIA|MOTOCROSS|MOTOCICLISTA|AUTOMOVIL|AUTOMOVIL CLUB|CLASICOS|4X4|CIRCUITO|CIRCUIT|CIRCUITS",
    "badminton": "BADMINTON",
    "tenis_de_mesa": "TENIS DE MESA|TENIS TAULA|TENNIS DE TAULA|PING PONG|TENIS MESA|TENNIS TAULA",
    "halterofilia_lucha": "HALTEROFILIA|LUCHA|LUCHA CANARIA|LUCHAS|LUCHA LEONESA|POWERLIFTING|FISICOCULTURISMO|CULTURISMO|HERRI KIROLAK|HERRI KIROL|SOKATIRA|LLUITA|LOITA|FITNESS|CROSSFIT|MUSCULACION|LEVANTAMIENTO",
    "orientacion": "ORIENTACION|ORIENTACIO",
    "beisbol_softbol": "BEISBOL|SOFTBOL|BASEBALL|SOFBOL",
    "squash": "SQUASH|RAQUETA|RAQUETAS",
    "aeronautica": "AERONAUTICO|AERONAUTICA|AEREO|AERO CLUB|AEROCLUB|PARAPENTE|VUELO|AEROMODELISMO|PARACAIDISMO|ALA DELTA",
    "deporte_adaptado": "ADAPTADO|ADAPTADA|ADAPTAT|ADAPTADOS|ADAPTATS|DISCAPACIDAD|DISCAPACITADOS|DISCAPACITATS|PARALIMPICO|PARALIMPIC|DIVERSIDAD FUNCIONAL|SORDOS|CIEGOS|PARALISIS CEREBRAL|PARALITICOS CEREBRALES|INTELECTUAL|MINUSVALIDOS|SPECIAL OLYMPICS|CAPACIDADES DIFERENTES|INCLUSIVO|INCLUSIVA|INCLUSIU|DISCAPACIDADE",
    "caza_pesca": "CAZA|CAZADORES|PESCA|PESCADORES|CACA|CACADORS|EHIZA|ARRANTZA|CASTING|GALGOS|CETRERIA",
    "otros_deportes": "BILLAR|COLOMBOFILO|COLOMBOFIL|DARDOS|PENTATLON|BAILE DEPORTIVO|COLOMBOFILA|COLOMBOFILIA|COLUMBICULTURA|COLOMBICULTURA|CANINA|AGILITY|E SPORTS|ESPORTS ELECTRONICOS|DEPORTES ELECTRONICOS|GAMING|DEPORTES TRADICIONALES|JOCS TRADICIONALS|JUEGOS TRADICIONALES|JUEGOS Y DEPORTES|TAMBORIL|FRISBEE|ULTIMATE|HOCKEY LINEA|KORFBAL|LACROSSE|CRIQUET|CRICKET|DEPORTES AEREOS|TWIRLING|KIN BALL|CHEERLEADING|DANZA DEPORTIVA|BAILE|DANCE|YOGA|PILATES",
}
AMBIGUAS = set("""CROSS MARCHA TRAIL RUNNING CORREDORES BICI BICICLETA BIKE PATIN ROLLER SKATE AEROBIC TRAMPOLIN REMO REM CANOA
KAYAK VELA NAUTICO NAUTIC NAUTICA MARITIMO SURF REGATAS REGATA SALVAMENTO SOCORRISMO SALVAMENT POLO CABALLO CABALLOS
ENGANCHES RAID DOMA MONTANA MUNTANYA MENDI ALPINO SENDERISMO EXCURSIONISTA EXCURSIONISMO ESPELEO TREKKING ESQUI HIELO
GELO GEL ESKI BOLO BOLA BOLEROS BOLERAS PELOTA PILOTA PALETA FRONTON TIRO TIR ARCO ARQUEROS ARQUERS TIRADORES ARKU MOTOR
MOTO MOTOS RALLY RALLYE TRIAL ENDURO ESCUDERIA AUTOMOVIL CLASICOS 4X4 CIRCUITO CIRCUIT CIRCUITS LUCHA LUCHAS LLUITA LOITA
FITNESS CROSSFIT MUSCULACION LEVANTAMIENTO ORIENTACION ORIENTACIO RAQUETA RAQUETAS AEREO VUELO PARAPENTE PARACAIDISMO
ADAPTADO ADAPTADA ADAPTAT ADAPTADOS ADAPTATS DISCAPACIDAD DISCAPACITADOS DISCAPACITATS SORDOS CIEGOS INTELECTUAL
MINUSVALIDOS INCLUSIVO INCLUSIVA INCLUSIU DISCAPACIDADE CAZA CAZADORES PESCA PESCADORES CACA CACADORS EHIZA ARRANTZA
CASTING GALGOS CETRERIA CANINA KITE SKI ANDARINES CAMINANTES BOLERA AGILITY GAMING BAILE DANCE YOGA PILATES TAMBORIL ULTIMATE MARATHON ATLETAS ATLETES
SINCRONIZADA MMA CF FC""".split()) | {"PARALISIS CEREBRAL", "PARALITICOS CEREBRALES", "DIVERSIDAD FUNCIONAL",
                                       "CAPACIDADES DIFERENTES", "JUEGOS Y DEPORTES", "MOTO CLUB", "AUTOMOVIL CLUB"}
SPORT_PATS = [(k, re.compile(r"\b(" + "|".join(sorted(v.split("|"), key=len, reverse=True)) + r")\b"))
              for k, v in SPORT_RX.items()]
DEPORT = re.compile(r"\b(\w*DEPORT\w*|\w*ESPORT\w*|KIROL\w*|SPORT\w*|POLIDEPORTIV\w*|POLIESPORTIU|ALTO RENDIMIENTO|ALT RENDIMENT|TECNIFICACION|OLIMPICO|OLIMPIC|PARALIMPICO|PARALIMPIC|ATLETICO|ATLETIC|ATHLETIC|FITNESS|GIMNASIO|GIMNAS|GYM)\b")
FED = re.compile(r"^(F E|R F E)\b|\b(FEDERACION|FEDERACIO|FEDERAZIO|FEDERACIONES|FEDERACIONS|FED|FEDER|FEDERAC|FEDERACAO|RFE[A-Z]*)\b")
FED_NACIONAL = re.compile(r"^(F E|R F E)\b|\b(ESPANOLA|ESPANOL|DE ESPANA|ESP|RFE[A-Z]*)\b")
OLIMP = re.compile(r"\b(COMITE OLIMPICO|COMITE PARALIMPICO)\b")
SAD = re.compile(r"\b(S ?A ?D|SOCIEDAD ANONIMA DEPORTIVA)\b")
# Estructuras de club. Las siglas sólo cuentan al principio del nombre y para NIF G (asociaciones).
CLUB = re.compile(r"\b(CLUB|CLUBS|CLUBE|CLUBES|KLUB|KLUBA|KIROL TALDEA|ESCUDERIA|MOTOCLUB|AEROCLUB|PENA|PENYA|AGRUPACION|UNION|UNIO|SOCIEDAD|SOCIETAT|ASOCIACION|ASOCIACIO|ASSOCIACIO|ASOC|ASSOC|ESCUELA|ESCOLA|SOCIEDADE|AGRUPAMENTO|GIMNASIO|ELKARTEA|TALDEA|GRUPO|GRUP|SECCION|SECCIO|SEKZIOA)\b")
CLUB_FUERTE = re.compile(r"\b(CLUB|CLUBS|CLUBE|CLUBES|KLUB|KLUBA|KIROL TALDEA|ESCUDERIA|MOTOCLUB|AEROCLUB)\b")
SIGLAS = re.compile(r"^(C ?D|C ?F|U ?D|S ?D|A ?D|C ?B|C ?N|U ?E|C ?E|E ?M ?F|C ?P|A ?E)\b")
SIGLAS_FUTBOL = re.compile(r"^(C ?F|U ?D|E ?M ?F)\b|\b(C ?F|F ?C)$")
ADMIN = re.compile(r"\b(CONSELLERIA|CONSEJERIA|MINISTERIO|DEPARTAMENTO|DEPARTAMENT|SECRETARIA|DIRECCION GENERAL|DIRECCIO GENERAL|GOBIERNO|GOBERN|GOVERN|XUNTA|JUNTA DE|GENERALITAT|DIPUTACION|DIPUTACIO|CABILDO|AYUNTAMIENTO|AJUNTAMENT|CONCELLO|UDALA|COMUNIDAD AUTONOMA|UNIVERSIDAD|UNIVERSITAT|UNIVERSIDADE|CONSEJO INSULAR|CONSELL INSULAR|CONSELL COMARCAL|MANCOMUNIDAD|CIUDAD AUTONOMA)\b")
PUBLICA = re.compile(r"\b(PATRONATO|PATRONAT|INSTITUTO|INSTITUT|FUNDACION|FUNDACIO|CONSORCIO|CONSORCI|SERVICIO|SERVEI|ORGANISMO|ORGANISME|CONSELL|CONSEJO|EMPRESA|SOCIEDAD|AGENCIA|CENTRO|CENTRE|ESCUELA|ESCOLA|ALTO RENDIMIENTO|ALT RENDIMENT)\b")
NEG = re.compile(r"\b(HOSPITAL|COLEGIO|COLEGI|COLEXIO|CEIP|IES|AMPA|AMPAS|APA|PARROQUIA|HERMANDAD|COFRADIA|CONFRARIA|CONFRARIES|CONFRARIAS|PESCADORES|MUSICA|MUSICAS|MUSICAL|LUCHA CONTRA|ENFERMEDAD|ENFERMEDADES|ENFERMOS|SINDICATO|COMUNIDAD DE REGANTES|FARMACIA|CLUB DE LECTURA|CLUB DE JUBILADOS|CLUB DE PENSIONISTAS|CLUB DE LA TERCERA EDAD|CLUB DE MAYORES|CLUB SOCIAL|CLUB DEL PENSIONISTA|ROTARY|LIONS|CLUB DE EMPRESAS|CLUB DE MARKETING|CLUB DE INVERSION|ENSAYO CLINICO|PESCA MARITIMA|COFRADIA DE PESCADORES|PESCADORES DE|EDICIONES|EDITORIAL|MUNDO DEPORTIVO|DIARIO|PRENSA|TELEVISION|RADIO|PERIODICO|NUTRITION|SPORTWEAR|SPORTSWEAR|MANUFACTURAS|TEXTIL|CALZADO|HOSTEL|HOTEL|CAMPING|APARTAMENTOS|PUERTOS DEPORTIVOS|PUERTO DEPORTIVO|PORT ESPORTIU|MARINA|AUTOCARES|TRANSPORTES|SEGUROS|CONSULTING|INMOBILIARIA|CONSTRUCCIONES|SUMINISTROS|DISTRIBUCION|DISTRIBUCIONES|ARMERIA|ARMAS|TALLER|TALLERES|TAXI|AUTOCAR|AUTOMOVILES|CONCESIONARIO|MOTORES|AUTOMOCION|ELECTRICIDAD|FONTANERIA|VIVERO|GANADERIA|GANADEROS|AGRICOLA|AGRARIA|CLUB DE VINOS|CLUB DEL VINO|CLUB DE PRODUCTO|CENTRO DE DIA|CENTRE DE DIA|CARAVANING|CARAVANAS|MOTOR SL|MOTOR S L|MOTOR SA|MOTOR S A|VINOS|BODEGA|BODEGAS|CRIADORES|RAZA)\b")

TIPOS = ["federacion_nacional", "federacion_autonomica", "club", "sad", "empresa_deportiva", "entidad_publica", "otro"]
TIPO_LABEL = {"federacion_nacional": "Federación española", "federacion_autonomica": "Federación autonómica o territorial",
              "club": "Club o asociación deportiva", "sad": "Sociedad anónima deportiva / club mercantil",
              "empresa_deportiva": "Empresa deportiva (gestión, instalaciones, gimnasios, eventos)",
              "entidad_publica": "Entidad pública deportiva (patronatos, institutos, consorcios, CAR)",
              "otro": "Otras entidades deportivas (fundaciones, COE/CPE, asociaciones sin forma de club)"}


def sports_in(n: str) -> list[tuple[str, str, bool]]:
    out = []
    for k, rx in SPORT_PATS:
        for m in rx.finditer(n):
            w = m.group(0)
            out.append((k, w, w not in AMBIGUAS))
    return out


def deporte_de(n: str, contexto: bool) -> str:
    """Deporte inferido del nombre. 'sin_clasificar' si no hay palabra de deporte fiable."""
    s = sports_in(n)
    if SIGLAS_FUTBOL.search(n):
        s.append(("futbol", "CF", True))
    fuertes = [x for x in s if x[2]] or (s if contexto else [])
    if not fuertes:
        return "sin_clasificar"
    fuertes.sort(key=lambda x: -len(x[1]))  # «TENIS DE MESA» antes que «TENIS»
    return fuertes[0][0]


def clasificar(nif: str, raw: str) -> tuple[str, str] | None:
    """-> (tipo_beneficiario, deporte) o None si el nombre no es deportivo."""
    n = norm(raw)
    if not n:
        return None
    letra = nif[0]
    dep, fed, club, sad = DEPORT.search(n), FED.search(n), CLUB.search(n), SAD.search(n)
    fuerte = CLUB_FUERTE.search(n) or (letra == "G" and SIGLAS.search(n))
    sp = sports_in(n)
    sp_fuerte = any(x[2] for x in sp) or bool(SIGLAS_FUTBOL.search(n))
    es_caza = sp and all(x[0] == "caza_pesca" for x in sp)
    if OLIMP.search(n):
        return "otro", deporte_de(n, True)
    sp_fed = sp_fuerte or any(x[0] != "deporte_adaptado" for x in sp)  # «FED. DE VELA» vale; «FED. DE PERSONAS CON DISCAPACIDAD» no
    if fed and (dep or sp_fed) and not NEG.search(n) and not (letra in "PQS" and ADMIN.search(n)):
        return ("federacion_nacional" if FED_NACIONAL.search(n) else "federacion_autonomica"), deporte_de(n, True)
    # Exclusiones: palabras de otro sector (prensa, hostelería, talleres...) y administraciones generales.
    # A una asociación (G) con DEPORT* en el nombre no la excluye NEG; a una empresa, sí (p. ej. «EDICIONES DEPORTIVAS»).
    if NEG.search(n) and (letra in "ABCDEJUV" or not dep):
        return None
    if ADMIN.search(n) and letra not in "GFRNW":
        return None
    if es_caza and not dep:  # sociedades de cazadores / pescadores sin «deportivo» en el nombre: fuera
        return None
    if letra in "PQS":
        return ("entidad_publica", deporte_de(n, True)) if dep and PUBLICA.search(n) else None
    if sad:
        return "sad", deporte_de(n, True)
    if letra in "ABCDEJUV":
        if fuerte and (dep or sp_fuerte):
            return "sad", deporte_de(n, True)  # club con forma mercantil (SL/SA sin «SAD» en el nombre)
        return ("empresa_deportiva", deporte_de(n, True)) if dep else None
    # G (asociaciones/fundaciones), F, R, N, W
    if dep:
        return ("club" if club or fuerte else "otro"), deporte_de(n, True)
    if fuerte and (sp or sp_fuerte):
        return "club", deporte_de(n, True)
    if club and sp_fuerte:
        return "club", deporte_de(n, True)
    return None


# ------------------------------------------------------------------ validación manual (muestra fija)
# Muestra de 100 entidades extraída con random.Random(18): 50 positivos al azar y 50 negativos cuyo nombre
# contiene una palabra ambigua (DEPORT*, CLUB, SPORT*, ESPORT*). Juzgada a mano una sola vez (criterio: entidad
# cuya actividad principal es practicar u organizar un deporte reconocido/federado). Queda fijada por NIF para que
# el informe sea reproducible; el resumen se calcula con la clasificación ACTUAL de cada NIF, así que si el
# clasificador cambia, la precisión publicada se recalcula sobre la misma muestra.
VALIDACION: dict[str, tuple[str, bool]] = {  # nif: (grupo al muestrear, ¿es entidad deportiva?)
    "G16739245": ("positivo", True),  # CLUB XADREZ AS BURGAS
    "G10286086": ("positivo", True),  # CLUB DEPORTIVO LOCAL DE CAZA LOGROS
    "G59746230": ("positivo", True),  # CLUB TENIS RIPOLLET
    "G41552118": ("positivo", True),  # CLUB BADMINTON LA RINCONADA
    "G27206622": ("positivo", True),  # SOCIEDADE DEPORTIVA DE CAZADORES NEGUEIRA DE MUÑIZ
    "G19287101": ("positivo", True),  # C.D. CICLISTA CICLO-ROOM EL CASAR
    "G70417548": ("positivo", True),  # ESCOLA NAUTICA DEPORTIVA DE BOIRO
    "V57461568": ("positivo", True),  # CLUB ESPORTIU BLAU
    "G70681440": ("positivo", True),  # CLUB PETANCA ALOVERA
    "G16885808": ("positivo", True),  # CLUB GELIDA FEM GYM
    "G67227355": ("positivo", True),  # ASSOCIACIO ESPORTIVA JUNIORS MASNOU
    "G36147080": ("positivo", True),  # CLUB MARCON ATLETICO
    "G61538229": ("positivo", True),  # CLUB ESPORTIU FUTBOL SALA SANT JOAN DE VILASSAR
    "G31912207": ("positivo", True),  # CLUB DEPORTIVO MUTILBASKET
    "G19022573": ("positivo", True),  # ASOC. DEPORTIVO CULTURAL DE ALARILLA
    "G30448427": ("positivo", True),  # ASOC DEPORTIVA BUDOKAN DE ALCANTARILLA
    "G09757576": ("positivo", True),  # ASOCIACION CULTURAL E DEPORTIVA ANDAINA
    "G39456173": ("positivo", True),  # AD SOCIEDAD DEPORTIVA DE REMO CASTREÑA
    "G76099365": ("positivo", True),  # CLUB DEPORTIVO DE BOLAS JUAN BARRIOS
    "G15794589": ("positivo", True),  # CLUB ESCOLAS DE FUTBOL LUIS CALVO SANZ
    "G26284281": ("positivo", True),  # CLUB CICLISTA RADIKAL BIKE COMPANY
    "G15321060": ("positivo", True),  # SOCIEDAD DEPORTIVA SAN LORENZO
    "G27041631": ("positivo", True),  # SOC. DEPORTIVA OURAL
    "G19417930": ("positivo", True),  # UNIÓ CICLISTA LA GARRIGA UNIÓ CICLISTA LA GARRIGA
    "G46637989": ("positivo", True),  # BASQUET CLUB MELIANA
    "G93183846": ("positivo", True),  # CLUB DEPORTIVO SOHO MALAGA
    "G72964026": ("positivo", True),  # C.D. CICLISTA CARAQUIZ-UCEDA
    "G19630649": ("positivo", True),  # CLUB DEPORTIVO CGC RIDERS
    "G70636154": ("positivo", True),  # EME AUTOMOBILISMO KIROL KLUBA
    "G22592729": ("positivo", True),  # CLUB RITMICA XOVE
    "G36337533": ("positivo", True),  # CLUB DE FUTBOL LAMELA
    "G32024812": ("positivo", False),  # ASOC VECINAL CULTURAL DEPORTIVA DE BOVED
    "B04562302": ("positivo", True),  # TOYO AVENTURA ACTIVIDADES DEPORTIVAS, SL
    "G43091560": ("positivo", True),  # POLIESPORTIU EL GARRIGO
    "G54309406": ("positivo", True),  # CLUB DEPORTIVO TRIASPE
    "G24283616": ("positivo", True),  # CLUB DEPORTIVO CUATROVIENTOS
    "G54399084": ("positivo", True),  # CLUB VOLEIBOL FINESTRAT
    "G79345542": ("positivo", True),  # CLUB DEPORTIVO UNION DE ARAVACA . .
    "G43433655": ("positivo", True),  # CAMBRILS CLUB NATACIO
    "G96313622": ("positivo", True),  # CLUB DEPORTIVO ORRIOLS MARNI
    "G92289339": ("positivo", True),  # CLUB BADMINTON ALHAURIN DE LA TORRE
    "G76305952": ("positivo", True),  # CLUB COLOMBOFILO BIOSFERA
    "G33346016": ("positivo", True),  # CLUB DEPORTIVO TINEO
    "G32478034": ("positivo", True),  # ESCOLAS DEPORTIVAS NOGUEIRA DE RAMUIN
    "G97797021": ("positivo", True),  # ASSOCIACIO AMICS DEL TENIS D'ALGEMESI
    "G36663664": ("positivo", True),  # FEDERACIÓN GALEGA DE MOTONÁUTICA
    "G83212472": ("positivo", True),  # CLUB TENIS DE MESA ALCALA VILLALBILLA
    "G09248238": ("positivo", True),  # ASOCIACION CULTURAL DEPORTIVA SAN JUAN BAUTISTA
    "G35232974": ("positivo", True),  # CLUB DE LUCHA CANARIA MANINIDRA
    "G66859349": ("positivo", True),  # VILASSAR DE MAR BIKERS CLUB CICLISTA 2016
    "G39201231": ("negativo_ambiguo", False),  # CLUB DE LA TERCERA EDAD DE MIENGO
    "G98820681": ("negativo_ambiguo", False),  # OFFICIAL FAN CLUB JORGE NAVARRO
    "G33734674": ("negativo_ambiguo", False),  # CLUB VICTORIA DE PERLORA - CARREÑO
    "G01129329": ("negativo_ambiguo", False),  # CLUB MONTE ALEGRE
    "G33216607": ("negativo_ambiguo", False),  # CLUB POPULAR DE CULTURA LLARANES
    "G53339636": ("negativo_ambiguo", False),  # CLUB DE CONVIVENCIA DE PENSIONISTES Y JUBILATS DE ORXETA
    "G70257670": ("negativo_ambiguo", True),  # LA VIEJA ESCUELA BOARDING CLUB
    "G48262398": ("negativo_ambiguo", False),  # BERRIO-OTXOA ASTII BILTOKIA (CLUB DE TIEMPO LIBRE)
    "G70223169": ("negativo_ambiguo", False),  # CLUB ACORDES PONTEDEUME
    "G02205045": ("negativo_ambiguo", False),  # ASOC CLUB DE JUBILADOS CANAL DE MARIA CRISTINA DE
    "G04038790": ("negativo_ambiguo", False),  # CLUB TERCERA EDAD CORTIJOS DE MARIN
    "G06858799": ("negativo_ambiguo", False),  # CLUB PONTUS VETERIS
    "G49017312": ("negativo_ambiguo", False),  # CLUB JUB. VILLANUEVA DEL CAMPO
    "G53561452": ("negativo_ambiguo", False),  # CLUB
    "G70761853": ("negativo_ambiguo", False),  # CLUB XUVENTUDE LARACHA
    "G30631485": ("negativo_ambiguo", False),  # CLUB DE LA TERCERA EDAD DE LOS DOLORES
    "B96727433": ("negativo_ambiguo", False),  # ARTS SPORTS CONSULTING SL
    "G27804970": ("negativo_ambiguo", False),  # CLUB PEÑASCO
    "G35425602": ("negativo_ambiguo", False),  # CLUB TAMARAN GRAN CANARIA
    "G32004244": ("negativo_ambiguo", False),  # CLUB SOCIAL SANTO DOMINGO
    "G39801345": ("negativo_ambiguo", False),  # ASOC UNIFICADA PEQUEÑOS ACCIONISTAS DEL REAL RACING CLUB
    "B71029367": ("negativo_ambiguo", False),  # DEPORTE Y DISTRIBUCIÓN TEXTIL NAVARRA S.L.U.
    "G96831276": ("negativo_ambiguo", False),  # ALJAZZIRA JAZZ CLUB
    "G56681141": ("negativo_ambiguo", True),  # CLUB DEPOR ELEMENT CONTACT WEIGHTLIFTING
    "G06470777": ("negativo_ambiguo", False),  # ASOC CULTURAL CINE CLUB FORUM DE ME
    "G43084474": ("negativo_ambiguo", True),  # PATI CLUB VILA-SECA
    "G12253159": ("negativo_ambiguo", False),  # CLUB CAZADORES SAGANTA DE ESPADILLA
    "G36524171": ("negativo_ambiguo", False),  # CLUB DE PESCA MARITIMA O ISCO
    "G75864942": ("negativo_ambiguo", False),  # ASSOCIACIO CULTURAL CINE CLUB TERRA ALTA BOT
    "G17316399": ("negativo_ambiguo", False),  # ROTARY CLUB GIRONA
    "G70132170": ("negativo_ambiguo", True),  # CLUB AGUAMARINA SINCRO
    "G72499304": ("negativo_ambiguo", True),  # CLUB AUGA DRAGON BOAT BCS A CORUÑA
    "G73800120": ("negativo_ambiguo", True),  # CLUB MONTAÑERO DE YECLA
    "G73158479": ("negativo_ambiguo", False),  # CLUB PENSIONISTAS SAN JOSE
    "G49146426": ("negativo_ambiguo", False),  # CLUB GALGUERO LA MAGDALENA
    "G36782886": ("negativo_ambiguo", True),  # CLUB RACING VILARIÑO
    "G31348287": ("negativo_ambiguo", False),  # CLUB JUBILADOS Y PENSIONISTAS VIRGEN DE ALMUZA
    "B60256773": ("negativo_ambiguo", False),  # INFO 7 CLUB SLU
    "G32489890": ("negativo_ambiguo", True),  # CLUB ARQUEIROS DO SIL 2002
    "G01212976": ("negativo_ambiguo", True),  # CLUB ADURTZA  JAI-ALAI
    "G31681752": ("negativo_ambiguo", False),  # CLUB DE JUBILADOS SAN MARTIN
    "G01740893": ("negativo_ambiguo", True),  # PINATARIUS WRESTLING CLUB
    "G32431835": ("negativo_ambiguo", True),  # CLUB XADREZ CEIP PEREIRO DE AGUIAR
    "B56509102": ("negativo_ambiguo", False),  # CLUB TALENTO SIGLO XXI
    "G12207171": ("negativo_ambiguo", False),  # CLUB DE CAZADORES EL MAESTRAZGO DE MORELLA
    "G49024532": ("negativo_ambiguo", False),  # CLUB JUB. MORALES REY
    "B66191404": ("negativo_ambiguo", False),  # LA SANTA SANDWICH CLUB,SL
    "G36757276": ("negativo_ambiguo", False),  # CLUB O PANASCO
    "G19103746": ("negativo_ambiguo", False),  # CLUB DE TERCERA EDAD DE MASEGOSO DE TAJUÑA
    "G06711436": ("negativo_ambiguo", False),  # ASOCIACION CLUB CANARICULTORES DEL OESTE
}


# ------------------------------------------------------------------ helpers
def meta(desc: str, **extra) -> dict:
    return {"fuente": FUENTE, "url": API, "periodo": "2024-2025 (año de concesión)", "unidad": "EUR",
            "descripcion": desc,
            "metodo": "Beneficiario identificado como deportivo por el nombre (federaciones, clubes, SAD, patronatos, "
                      "empresas deportivas) o, como señal secundaria, por convocatoria con sectores CNAE exclusivamente 93.1x.",
            "limite": "Sólo entidades jurídicas; sólo subvenciones publicadas en BDNS (no contratos, ni cesiones de "
                      "instalaciones, ni gasto directo). Clasificador por nombre con error medido en data/informe.md.",
            **extra}


def pct(a: float, b: float) -> float | None:
    return round(100 * a / b, 2) if b else None


def r2(x: float) -> float:
    return round(x or 0, 2)


def write(name: str, obj) -> None:
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    print(f"  data/{name} {(DATA / name).stat().st_size // 1024} KB")


# ------------------------------------------------------------------ main
def main() -> int:
    DATA.mkdir(exist_ok=True)
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    q = lambda sql, *p: db.execute(sql, p).fetchall()  # noqa: E731

    # Señal 2: convocatorias cuyos sectores son sólo 93.1x
    conv931 = set()
    for num, sect in q("SELECT num, sectores FROM convocatoria WHERE sectores LIKE '%93.1%'"):
        s = json.loads(sect or "[]")
        if s and all(x.startswith("93.1") for x in s):
            conv931.add(num)

    # Una pasada sobre todas las concesiones. Clasificación a nivel de entidad (NIF):
    # positiva si alguno de sus nombres lo es; tipo/deporte del nombre con más importe.
    cache: dict[tuple[str, str], tuple[str, str] | None] = {}
    ent_tipo: dict[str, dict] = {}            # nif -> {tipo, deporte, importe, nombre}
    ent_nombre_imp: dict[str, Counter] = defaultdict(Counter)
    rows: list[tuple] = []
    n_total = Counter()
    imp_total = Counter()
    cur = db.execute("SELECT anio, tipo_admin, nivel1, nivel2, nivel3, num_conv, importe, nif, nombre, instrumento FROM concesion")
    for anio, ta, n1, n2, n3, nc, imp, nif, nombre, instr in cur:
        n_total[anio] += 1
        imp_total[anio] += imp
        key = (nif, nombre or "")
        if key not in cache:
            cache[key] = clasificar(nif, nombre or "")
        c = cache[key]
        ent_nombre_imp[nif][nombre or ""] += imp
        if c:
            e = ent_tipo.setdefault(nif, {"importe": -1})
            if imp > e["importe"] or e.get("tipo") is None:
                e.update(tipo=c[0], deporte=c[1], importe=imp, nombre=nombre)
        if c or nc in conv931:
            rows.append((anio, ta, n1, n2, n3, nc, imp, nif, nombre or "", c is not None, instr))
    del cache

    # Entidades captadas sólo por la señal 93.1 (nombre no evidente)
    for anio, ta, n1, n2, n3, nc, imp, nif, nombre, pos, _ in rows:
        if nif not in ent_tipo:
            ent_tipo[nif] = {"tipo": "entidad_publica" if nif[0] in "PQS" else "otro", "deporte": "sin_clasificar",
                             "importe": imp, "nombre": nombre, "via": "convocatoria_931"}
    for nif in ent_tipo:
        ent_tipo[nif]["nombre"] = ent_nombre_imp[nif].most_common(1)[0][0]
        ent_tipo[nif].setdefault("via", "nombre")

    # Concesiones deportivas definitivas (toda concesión de una entidad positiva, o de convocatoria 93.1)
    dep_rows = [r for r in rows if r[7] in ent_tipo]
    assert all(r[9] or r[5] in conv931 for r in dep_rows)

    agreg, top, organos, deportes = {}, {}, {}, {}
    for y in YEARS:
        R = [r for r in dep_rows if r[0] == y]
        tot = sum(r[6] for r in R)
        by_nif = defaultdict(lambda: {"importe": 0.0, "n": 0, "organos": Counter(), "conv": set()})
        for anio, ta, n1, n2, n3, nc, imp, nif, nombre, pos, _ in R:
            b = by_nif[nif]
            b["importe"] += imp
            b["n"] += 1
            b["organos"][(n1, n2, n3)] += imp
            b["conv"].add(nc)
        ents = len(by_nif)
        # por administración
        adm = Counter()
        admn = Counter()
        instr_imp, instr_n = Counter(), Counter()
        for r in R:
            adm[r[1]] += r[6]
            admn[r[1]] += 1
            instr_imp[r[10]] += r[6]
            instr_n[r[10]] += 1
        ADM = {"C": "Estado", "A": "Comunidades autónomas", "L": "Entidades locales", "O": "Otros"}
        # por tipo de beneficiario
        tipo_imp, tipo_n, tipo_e = Counter(), Counter(), defaultdict(set)
        via_imp, via_n = Counter(), Counter()
        for r in R:
            t = ent_tipo[r[7]]["tipo"]
            tipo_imp[t] += r[6]
            tipo_n[t] += 1
            tipo_e[t].add(r[7])
            v = "nombre" if r[9] else "solo_convocatoria_931"
            via_imp[v] += r[6]
            via_n[v] += 1
        # por deporte
        dep_imp, dep_n, dep_e = Counter(), Counter(), defaultdict(set)
        for r in R:
            d = ent_tipo[r[7]]["deporte"]
            dep_imp[d] += r[6]
            dep_n[d] += 1
            dep_e[d].add(r[7])
        # concentración
        imps = sorted((b["importe"] for b in by_nif.values()), reverse=True)
        k1 = max(1, round(len(imps) * 0.01))
        top10 = sum(imps[:10])
        top1pct = sum(imps[:k1])
        # fútbol profesional (SAD) frente al resto
        sad_fut = sum(r[6] for r in R if ent_tipo[r[7]]["tipo"] == "sad" and ent_tipo[r[7]]["deporte"] == "futbol")
        sad_otro = sum(r[6] for r in R if ent_tipo[r[7]]["tipo"] == "sad" and ent_tipo[r[7]]["deporte"] != "futbol")
        fut_all = sum(r[6] for r in R if ent_tipo[r[7]]["deporte"] == "futbol")
        agreg[str(y)] = {
            "total": {"importe": r2(tot), "concesiones": len(R), "entidades": ents,
                      "convocatorias": len({r[5] for r in R}),
                      "pct_sobre_todas_las_subvenciones_a_entidades": pct(tot, imp_total[y]),
                      "universo_bdns_entidades": {"importe": r2(imp_total[y]), "concesiones": n_total[y]}},
            "por_senal": [{"senal": v, "n": via_n[v], "importe": r2(via_imp[v]), "pct_importe": pct(via_imp[v], tot)}
                          for v in ("nombre", "solo_convocatoria_931")],
            "por_instrumento": [{"instrumento": k, "n": instr_n[k], "importe": r2(instr_imp[k]), "pct_importe": pct(instr_imp[k], tot)}
                                for k in sorted(instr_imp, key=lambda k: -instr_imp[k])],
            "por_administracion": [{"tipo_admin": k, "nombre": ADM[k], "n": admn[k], "importe": r2(adm[k]),
                                    "pct_importe": pct(adm[k], tot)} for k in sorted(adm, key=lambda k: -adm[k])],
            "por_tipo_beneficiario": [{"tipo": t, "nombre": TIPO_LABEL[t], "n": tipo_n[t], "entidades": len(tipo_e[t]),
                                       "importe": r2(tipo_imp[t]), "pct_importe": pct(tipo_imp[t], tot)}
                                      for t in TIPOS],
            "concentracion": {"entidades": ents, "top_1pct_entidades": k1, "top_1pct_importe": r2(top1pct),
                              "top_1pct_pct": pct(top1pct, tot), "top_10_importe": r2(top10), "top_10_pct": pct(top10, tot),
                              "mediana_por_entidad": r2(imps[len(imps) // 2]) if imps else None,
                              "media_por_entidad": r2(tot / ents) if ents else None},
            "futbol_vs_resto": {"sad_futbol": r2(sad_fut), "sad_futbol_pct": pct(sad_fut, tot),
                                "sad_otros_deportes": r2(sad_otro), "futbol_total_todos_los_tipos": r2(fut_all),
                                "futbol_total_pct": pct(fut_all, tot), "resto": r2(tot - fut_all),
                                "nota": "«SAD fútbol» = entidades con forma mercantil (SAD/SA/SL) cuyo nombre indica fútbol. "
                                        "Las SAD de fútbol sin «fútbol» en el nombre (p. ej. «REAL ZARAGOZA SAD») quedan en sad_otros."},
        }
        deportes[str(y)] = [{"deporte": d, "n": dep_n[d], "entidades": len(dep_e[d]), "importe": r2(dep_imp[d]),
                             "pct_importe": pct(dep_imp[d], tot)} for d in sorted(dep_imp, key=lambda d: -dep_imp[d])]
        topl = sorted(by_nif.items(), key=lambda kv: -kv[1]["importe"])[:100]
        top[str(y)] = [{"pos": i + 1, "nif": nif, "nombre": ent_tipo[nif]["nombre"], "tipo": ent_tipo[nif]["tipo"],
                        "deporte": ent_tipo[nif]["deporte"], "importe": r2(b["importe"]), "n": b["n"],
                        "convocatorias": len(b["conv"]),
                        "organo_principal": {"nivel1": o[0], "nivel2": o[1], "nivel3": o[2], "importe": r2(v),
                                             "pct_del_beneficiario": pct(v, b["importe"])}}
                       for i, (nif, b) in enumerate(topl) for o, v in [b["organos"].most_common(1)[0]]]
        org = defaultdict(lambda: [0, 0.0, set()])
        for r in R:
            o = org[(r[2], r[3], r[4])]
            o[0] += 1
            o[1] += r[6]
            o[2].add(r[7])
        organos[str(y)] = [{"pos": i + 1, "nivel1": k[0], "nivel2": k[1], "nivel3": k[2], "n": v[0], "entidades": len(v[2]),
                            "importe": r2(v[1]), "pct_importe": pct(v[1], tot)}
                           for i, (k, v) in enumerate(sorted(org.items(), key=lambda kv: -kv[1][1])[:25])]

    # Cuadre
    for y in YEARS:
        a = agreg[str(y)]
        assert abs(sum(t["importe"] for t in a["por_tipo_beneficiario"]) - a["total"]["importe"]) < 1
        assert sum(t["n"] for t in a["por_tipo_beneficiario"]) == a["total"]["concesiones"]
        assert abs(sum(t["importe"] for t in deportes[str(y)]) - a["total"]["importe"]) < 1

    # Muestra de validación (semilla fija): 50 positivos + 50 negativos con palabras ambiguas
    muestra, pool = muestra_validacion(ent_tipo, ent_nombre_imp)
    val = validacion_resumen(muestra, pool)

    write("agregados.json", {"meta": meta("Totales anuales de subvenciones al deporte: por administración, tipo de "
                                          "beneficiario, concentración y fútbol profesional frente al resto",
                                          tipos_beneficiario=TIPO_LABEL, validacion_clasificador=val),
                             **agreg})
    write("top_beneficiarios.json", {"meta": meta("Top 100 beneficiarios deportivos por año (sólo entidades jurídicas; "
                                                  "la BDNS anonimiza a las personas físicas y aquí ni siquiera se cargan)"),
                                     **top})
    write("organos.json", {"meta": meta("Top 25 órganos convocantes (nivel1/nivel2/nivel3) por importe concedido a "
                                        "beneficiarios deportivos"), **organos})
    write("deportes.json", {"meta": meta("Reparto por deporte inferido del nombre del beneficiario. «sin_clasificar» "
                                         "= nombre deportivo sin disciplina reconocible (p. ej. «CLUB DEPORTIVO X»)",
                                         deportes_reconocidos=list(SPORT_RX)), **deportes})
    write("muestra_validacion.json", {"meta": meta("Muestra fija (semilla 18) para medir a mano la precisión del clasificador: "
                                                   "50 positivos al azar y 50 negativos con palabras ambiguas (DEPORT*, CLUB, "
                                                   "SPORT, ESPORT). 'veredicto' lo rellena una persona en VALIDACION."),
                                      "resumen": val, "muestra": muestra})
    write("sources.json", {
        "fuente_principal": {"nombre": FUENTE, "url": "https://www.infosubvenciones.es/bdnstrans/GE/es/concesiones",
                             "api": API, "licencia": "Datos públicos (Ley 38/2003 General de Subvenciones, art. 20)",
                             "fichero_local": "quien-cobra/work/bdns.sqlite (episodio cci-09, sólo lectura)",
                             "periodo": "Concesiones con fecha de concesión en 2024 y 2025, según lo publicado en la BDNS hasta la descarga de cci-09 (altas hasta septiembre de 2026). La BDNS se sigue completando con retraso: ambos años pueden crecer."},
        "metodo": ["Clasificación del beneficiario por nombre (regex multilingüe ES/CA/EU/GL) en 7 tipos y 38 deportes.",
                   "Señal secundaria: convocatorias cuyos sectores CNAE son exclusivamente 93.1x "
                   f"({len(conv931)} convocatorias).",
                   "Clasificación a nivel de entidad (NIF): basta un nombre positivo.",
                   "Precisión medida a mano sobre data/muestra_validacion.json."],
        "limites": ["No es el gasto público total en deporte: faltan contratos, cesiones de instalaciones, gasto directo y "
                    "subvenciones no publicadas en BDNS.", "Clubes con nombre no evidente se pierden; empresas con «deporte» "
                    "en el nombre pueden colarse.", "Sólo dos ejercicios; la BDNS se completa con retraso y las cifras pueden crecer.",
                    "Personas físicas (deportistas becados) no incluidas: la sqlite de origen sólo carga entidades jurídicas."],
        "scripts": ["scripts/deporte_build.py"],
    })
    print("OK", {y: agreg[str(y)]["total"] for y in YEARS})
    return 0


def muestra_validacion(ent_tipo: dict, ent_nombre_imp: dict) -> tuple[list[dict], dict]:
    amb = re.compile(r"\b(DEPORT\w*|CLUB|CLUBS|SPORT\w*|ESPORT\w*)\b")
    pos = [nif for nif, e in ent_tipo.items() if e["via"] == "nombre"]
    neg = [nif for nif, names in ent_nombre_imp.items()
           if nif not in ent_tipo and amb.search(norm(names.most_common(1)[0][0]))]
    out = []
    for nif, (grupo, veredicto) in VALIDACION.items():
        e = ent_tipo.get(nif, {})
        out.append({"grupo_al_muestrear": grupo, "nif": nif, "nombre": ent_nombre_imp[nif].most_common(1)[0][0],
                    "clasificado_ahora": e.get("tipo") is not None, "tipo": e.get("tipo"), "deporte": e.get("deporte"),
                    "veredicto_es_deportiva": veredicto})
    pool = {"positivos_por_nombre": len(pos), "negativos_ambiguos": len(neg),
            "negativos_ambiguos_importe": r2(sum(sum(ent_nombre_imp[n].values()) for n in neg)),
            "positivos_por_nombre_importe": r2(sum(sum(ent_nombre_imp[n].values()) for n in pos))}
    return out, pool


def validacion_resumen(muestra: list[dict], pool: dict) -> dict:
    pos = [m["veredicto_es_deportiva"] for m in muestra if m["clasificado_ahora"]]
    neg = [m["veredicto_es_deportiva"] for m in muestra if not m["clasificado_ahora"]]
    drift = sum((m["grupo_al_muestrear"] == "positivo") != m["clasificado_ahora"] for m in muestra)
    return {"positivos_revisados": len(pos), "positivos_correctos": sum(pos), "precision_pct": pct(sum(pos), len(pos)),
            "negativos_ambiguos_revisados": len(neg), "negativos_que_si_eran_deportivos": sum(neg),
            "falsos_negativos_entre_ambiguos_pct": pct(sum(neg), len(neg)),
            "entidades_cuya_clasificacion_cambio_desde_el_muestreo": drift,
            "poblacion": pool,
            "nota": "Muestra fija de 50 positivos + 50 negativos ambiguos (random.Random(18)); veredicto humano en "
                    "VALIDACION del script. Los importes de 'poblacion' suman 2024+2025."}


if __name__ == "__main__":
    sys.exit(main())
