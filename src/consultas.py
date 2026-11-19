# -*- coding: utf-8 -*-
"""
Las consultas con que se recorre el catálogo de las tres cadenas.

Cada una es una búsqueda en los tres sitios y pasa a ser una categoría del comparador.
La lista vive aquí y no en el flujo de trabajo para que haya un solo lugar donde
agregar una categoría, y para que se pueda revisar y probar como cualquier otro código.

Dos advertencias para quien la amplíe:

  - El término tiene que ser el que usa la gente al buscar en el sitio de la cadena, no
    el nombre del pasillo. «Fiambres» devuelve poco; «jamón» devuelve el pasillo entero.

  - El emparejamiento entre cadenas rinde peor en lo que se vende a granel o con formato
    variable —carnes, frutas y verduras— porque el nombre publicado no declara un
    formato comparable. Esos productos entran igual al catálogo, pero es esperable que
    queden con menos comparaciones que los envasados.
"""

CONSULTAS = [
    # ── Despensa ─────────────────────────────────────────────────────────────
    "arroz", "fideos", "aceite", "azucar", "sal", "harina",
    "lentejas", "porotos", "garbanzos", "quinoa", "avena",
    "salsa de tomate", "mayonesa", "ketchup", "mostaza", "aceitunas", "vinagre",
    "caldo", "sopa", "pure de papas", "condimentos",
    "mermelada", "miel", "manjar", "leche condensada",

    # ── Conservas ────────────────────────────────────────────────────────────
    "atun", "jurel", "choritos", "duraznos en conserva", "choclo en conserva",

    # ── Desayuno y once ──────────────────────────────────────────────────────
    "cafe", "te", "cereal", "galletas", "pan de molde", "tortillas",
    "chocolate en polvo",

    # ── Lácteos y huevos ─────────────────────────────────────────────────────
    "leche", "yogurt", "queso", "mantequilla", "margarina", "crema", "huevos",

    # ── Carnes, aves y fiambres ──────────────────────────────────────────────
    "carne molida", "pollo", "cerdo", "pescado", "jamon", "salame", "vienesas",
    "longaniza", "hamburguesas",

    # ── Frutas y verduras ────────────────────────────────────────────────────
    "papas", "cebolla", "tomate", "palta", "platano", "manzana", "limon",
    "zanahoria", "lechuga", "naranja",

    # ── Congelados ───────────────────────────────────────────────────────────
    "helado", "pizza", "congelados", "nuggets",

    # ── Bebidas ──────────────────────────────────────────────────────────────
    "bebida", "agua mineral", "jugo", "bebida energetica",

    # Alcoholes. Se incluyen porque forman parte del catálogo que las cadenas
    # publican abiertamente y de la canasta que la gente compara. El sistema solo
    # muestra el precio publicado y enlaza al sitio de origen; no vende ni promueve
    # consumo, que es lo que regula la Ley 19.925.
    "cerveza", "vino", "pisco", "ron",

    # ── Snacks y dulces ──────────────────────────────────────────────────────
    "papas fritas", "chocolate", "caramelos", "frutos secos",

    # ── Aseo del hogar ───────────────────────────────────────────────────────
    "detergente", "suavizante", "cloro", "lavalozas", "limpiapisos", "desinfectante",
    "esponja", "bolsa de basura", "papel higienico", "toalla de papel", "servilletas",
    "insecticida", "ambientador",

    # ── Cuidado personal ─────────────────────────────────────────────────────
    "shampoo", "acondicionador", "jabon", "pasta de dientes", "cepillo de dientes",
    "desodorante", "toallas higienicas", "crema corporal", "afeitar",

    # ── Bebé ─────────────────────────────────────────────────────────────────
    "panales", "toallitas humedas", "leche infantil",

    # ── Mascotas ─────────────────────────────────────────────────────────────
    "alimento para perro", "alimento para gato", "arena sanitaria",

    # ── Otros ────────────────────────────────────────────────────────────────
    "pilas", "velas", "carbon",
]
