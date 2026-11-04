/*
 * Extractor de Fracttal para TodoGas CMMS (formato "fracttal-json-v1").
 *
 * Qué hace: lee, SOLO LECTURA, las ubicaciones, los activos, los protocolos
 * (planes de tarea) con sus subtareas y el historial de OTs de UNA sede, usando
 * la sesión ya abierta en one.fracttal.com. No guarda, no edita, no exporta por
 * correo: llama a los mismos métodos que usa la pantalla para mostrar datos.
 * Al final descarga un archivo .json que se importa en TodoGas con
 * `python manage.py importar_fracttal_json <archivo>`.
 *
 * Cómo usarlo:
 *   1. Entrar a https://one.fracttal.com con una cuenta que vea la sede.
 *   2. Abrir la consola del navegador (F12 > Consola), pegar este archivo y Enter.
 *   3. Ejecutar, por ejemplo:
 *        extraerFracttal({ sede: "NOMBRE DE LA SEDE" })
 *      Opciones:
 *        sede      texto que aparece en el nombre de la sede raíz (obligatorio)
 *        maxOts    tope de OTs del historial (por defecto, todas)
 *        estados   estados de OT a traer: 3 finalizadas, 4 canceladas (por defecto [3])
 *        firmas    incluir las firmas dibujadas (base64); pesan (por defecto true)
 *        descargar false para dejar el resultado en window.__ultimaExtraccion sin descargar
 *
 * Nunca imprime ni guarda el token de la sesión.
 */
(function () {
  const VERSION_APP = "Fracttal/5.12.01 web";
  const TIPOS = {1: "TEXT", 2: "BOOLEAN", 3: "NUMBER", 4: "VERIFICATION", 5: "READING_METER", 6: "GEOREFERENCE", 7: "DROPDOWN", 8: "DATE_TIME"};

  async function rpc(method, params) {
    const r = await fetch("/rpc/proxy", {
      method: "POST",
      headers: {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Authorization": "Bearer " + localStorage.getItem("id_token"),
        "x-version": VERSION_APP,
      },
      body: JSON.stringify([{id: crypto.randomUUID(), jsonrpc: "2.0", method, params}]),
    });
    const j = (await r.json())[0];
    if (j.error) throw new Error(method + ": " + (j.error.message || JSON.stringify(j.error)));
    return j.result || {data: [], total: 0};
  }

  // Pide todas las páginas de una lista.
  async function todo(method, params, limite = 200) {
    let out = [], start = 0, total = Infinity, page = 1;
    while (out.length < total) {
      const r = await rpc(method, {...params, page, start, limit: limite});
      const data = r.data || [];
      total = r.total ?? data.length;
      out = out.concat(data);
      if (data.length === 0) break;
      start += limite; page += 1;
    }
    return out;
  }

  const BASE_ITEMS = {sort: [], group: {property: ""}, is_tree: false, node: 0, id_custom_field_group: null, id_location: null, bread_crumbs: [{id: 0, field_1: "Inicio"}], filter: []};
  const nulo = (v) => (v === "" || v === undefined ? null : v);

  async function extraerFracttal({sede, maxOts = Infinity, estados = [3], firmas = true, descargar = true} = {}) {
    if (!sede) throw new Error("Falta la opción sede, por ejemplo extraerFracttal({sede: 'NOMBRE DE LA SEDE'})");
    const aviso = (m) => console.log("[extractor] " + m);
    const S = sede.toUpperCase();

    aviso("Ubicaciones…");
    const ubic = await todo("inventories.items_list", {...BASE_ITEMS, id_type_item: 1}, 500);
    // La sede raíz puede no venir en la lista (la cuenta solo ve lo que cuelga de
    // ella). Se reconoce por el primer tramo de la ruta "// SEDE/ PISO/ ..." y su id
    // es el primer número de path_node.
    const primerTramo = (ruta) => String(ruta || "").replace(/^\/\/\s*/, "").split("/")[0].trim();
    const raizDe = (u) => String(u.path_node).split(".")[0];
    const raices = new Map();
    for (const u of ubic) {
      const tramo = primerTramo(u.parent_description);
      if (tramo && tramo.toUpperCase().includes(S)) raices.set(raizDe(u), tramo);
      if (!tramo && String(u.description).toUpperCase().includes(S)) raices.set(String(u.path_node), u.field_1 || u.description);
    }
    if (!raices.size) throw new Error("No encontré una sede que contenga '" + sede + "'. ¿Esta cuenta la ve?");
    const prefijos = [...raices.keys()];
    const enSede = (pn) => prefijos.some((p) => String(pn) === p || String(pn).startsWith(p + "."));
    const yaListadas = new Set(ubic.map((u) => String(u.id)));
    const sintéticas = [...raices.entries()].filter(([id]) => !yaListadas.has(id)).map(([id, nombre]) => ({
      id: Number(id), id_parent: null, code: null, nombre, descripcion: nombre, direccion: null, ciudad: null, codigo_area: null,
      departamento: null, pais: null, latitud: null, longitud: null, ruta: "// ", path_node: id, habilitado: true, barcode: null, notas: null,
      reconstruida: true,
    }));
    const ubicaciones = sintéticas.concat(ubic.filter((u) => enSede(u.path_node)).map((u) => ({
      id: u.id, id_parent: u.id_parent, code: u.code, nombre: u.field_1, descripcion: u.description,
      direccion: nulo(u.field_2), ciudad: nulo(u.field_3), codigo_area: nulo(u.field_4), departamento: nulo(u.field_5), pais: nulo(u.field_6),
      latitud: nulo(u.latitude), longitud: nulo(u.longitud), ruta: u.parent_description, path_node: u.path_node, habilitado: u.active,
      barcode: nulo(u.barcode), notas: nulo(u.notes),
    })));
    aviso(ubicaciones.length + " ubicaciones");

    aviso("Activos…");
    const acts = await todo("inventories.items_list", {...BASE_ITEMS, id_type_item: 2}, 500);
    const activos = acts.filter((a) => enSede(a.path_node)).map((a) => ({
      id: a.id, id_parent: a.id_parent, code: a.code, barcode: nulo(a.barcode), descripcion: a.description,
      nombre: a.field_1, fabricante: nulo(a.field_2), modelo: nulo(a.field_3), serie: nulo(a.field_4), ubicacion_equipo: nulo(a.field_5), otro: nulo(a.field_6),
      ruta: a.parent_description, path_node: a.path_node, habilitado: a.active, disponible: a.available,
      id_plan: a.id_group_task, plan: nulo(a.groups_tasks_description), prioridad: nulo(a.priorities_description),
      centro_costo: nulo(a.costs_center_description), clasificacion_1: nulo(a.groups_1_description), clasificacion_2: nulo(a.groups_2_description),
      notas: nulo(a.notes),
    }));
    aviso(activos.length + " activos");
    const idsActivos = new Set(activos.map((a) => a.id));

    aviso("Protocolos y subtareas…");
    const idsPlanes = [...new Set(activos.map((a) => a.id_plan).filter(Boolean))];
    const planes = [];
    for (const idp of idsPlanes) {
      const tareas = await todo("tasks.tasks_list", {filter: [{property: "id_group_task", operator: "=", value: idp}], sort: []});
      const t2 = [];
      for (const t of tareas) {
        const items = await todo("tasks.tasks_form_items_list", {id_task: t.id});
        t2.push({
          id: t.id, descripcion: t.description, duracion_seg: t.duration, activa: t.is_active,
          tipo: nulo(t.tasks_types_description), tipo_principal: nulo(t.tasks_types_main_description), tipo_2: nulo(t.tasks_types_2_description),
          prioridad: nulo(t.priorities_description), paro_activo: t.stop_assets, paro_seg: t.stop_assets_sec,
          iteraciones: {num: t.num_iterations, nombre: nulo(t.name_iterations), ciclica: t.is_cyclical},
          subtareas: items.map((f) => ({
            id: f.id, descripcion: f.description, tipo: TIPOS[f.id_task_form_item_type] || String(f.id_task_form_item_type),
            grupo: nulo(f.task_form_item_group_description), orden: f.order_number, requerida: f.is_required,
            unidad: nulo(f.units_code), opciones: (f.dropdown_options || []).map((o) => o.description), iteraciones: f.iterations || {},
            adjuntos_requeridos: f.attachments_required,
          })),
        });
      }
      planes.push({id: idp, nombre: (activos.find((a) => a.id_plan === idp) || {}).plan, tareas: t2});
    }
    aviso(planes.length + " protocolos");

    aviso("Activadores de tareas pendientes…");
    const pend = await todo("tasks.tasks_todo_list_kanban", {append: true, is_tree: false, id_type_item: 0, filter: [], group: {}, sort: [], utc_min: -300});
    const activadores = pend.filter((p) => idsActivos.has(p.id_item)).map((p) => ({
      id_activo: p.id_item, id_tarea: p.id_task, activador: nulo(p.trigger_description), proxima: nulo(p.date_maintenance),
      ultima: nulo(p.last_date_maintenance), duracion_seg: p.duration, descripcion: p.description,
    }));

    aviso("Historial de OTs…");
    let lista = [];
    for (const est of estados) {
      lista = lista.concat(await todo("tasks.work_orders_list_react", {append: true, id_status_work_order: est, filter: [{property: "parent_description", operator: "like", value: sede}], sort: []}));
    }
    lista = lista.slice(0, maxOts);
    const ots = [];
    let n = 0;
    for (const w of lista) {
      n += 1;
      if (n % 25 === 0) aviso("OT " + n + " de " + lista.length);
      const tareas = await todo("tasks.work_orders_tasks_new_list", {filter: [], sort: [], is_tree: false, node: null, id_work_order: w.id});
      const t2 = [];
      for (const t of tareas) {
        if (!idsActivos.has(t.id_item)) continue;
        const items = await todo("tasks.work_orders_task_form_items_list", {id_work_order_task: t.id});
        let archivos = [];
        try { archivos = await todo("tasks.work_orders_tasks_files_list", {id_work_order_task: t.id}); } catch (e) { archivos = []; }
        t2.push({
          id: t.id, id_tarea: t.id_task, id_activo: t.id_item, descripcion: t.tasks_description, activo: t.items_log_description,
          inicio: nulo(t.initial_date), fin: nulo(t.final_date), programada: nulo(t.date_maintenance), duracion_seg: t.duration,
          duracion_real_min: t.real_duration, paro_seg: t.real_stop_assets_sec, tecnico: nulo(t.personnel_description),
          tipo: nulo(t.tasks_types_description), tipo_principal: nulo(t.tasks_types_main_description), activador: nulo(t.trigger_description),
          prioridad: nulo(t.priorities_description), nota: nulo(t.note), nota_tarea: nulo(t.task_note), calificacion: t.rating,
          firma: firmas ? nulo(t.signature) : null, hecha: t.done,
          subtareas: items.map((f) => ({
            id_plan_subtarea: f.id_tasks_form_items, descripcion: f.description, tipo: TIPOS[f.id_task_form_item_type] || String(f.id_task_form_item_type),
            grupo: nulo(f.task_form_item_group_description), orden: f.order_number, valor: nulo(f.value), unidad: nulo(f.units_code), hecha: f.done,
          })),
          archivos: archivos.map((a) => ({ruta: a.value, nombre: a.end_value, descripcion: nulo(a.description), fecha: a.creation_date, id_subtarea: a.id_work_orders_tasks_form_items})),
        });
      }
      if (!t2.length) continue;
      ots.push({
        id: w.id, folio: w.wo_folio, estado: w.id_status_work_order, creada: w.creation_date, creada_por: nulo(w.created_by),
        responsable: nulo(w.personnel_description || w.user_assigned), nota: nulo(w.note), calificacion: w.rating,
        clasificaciones: nulo(w.labels), tareas: t2,
      });
    }
    aviso(ots.length + " OTs con tareas de la sede");

    const salida = {formato: "fracttal-json-v1", extraido: new Date().toISOString(), sede, ubicaciones, activos, planes, activadores, ots};
    window.__ultimaExtraccion = salida;
    const blob = new Blob([JSON.stringify(salida)], {type: "application/json"});
    if (!descargar) {
      aviso("Sin descarga: el resultado quedó en window.__ultimaExtraccion (" + Math.round(blob.size / 1024) + " KB)");
      return {ubicaciones: ubicaciones.length, activos: activos.length, protocolos: planes.length, ots: ots.length, kb: Math.round(blob.size / 1024)};
    }
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "fracttal-" + sede.toLowerCase().replace(/[^a-z0-9]+/g, "-") + "-" + new Date().toISOString().slice(0, 10) + ".json";
    a.click();
    aviso("Listo: " + a.download + " (" + Math.round(blob.size / 1024) + " KB)");
    return {ubicaciones: ubicaciones.length, activos: activos.length, protocolos: planes.length, ots: ots.length, kb: Math.round(blob.size / 1024)};
  }

  window.extraerFracttal = extraerFracttal;
  console.log("[extractor] Listo. Ejecuta: extraerFracttal({ sede: 'NOMBRE DE LA SEDE' })");
})();
