// Fotos de los lugares: Wikimedia Commons, con su autor y licencia (RN_13, se citan en "Acerca de").
// Una por cada lugar del catálogo (por su `clave`). Están recortadas a 3:2 (grande, 900 x 600) y
// 1:1 (mini, 200 x 200) y viven en public/fotos/, así que funcionan sin internet en el stand.
// Un lugar sin entrada aquí muestra un recuadro gris en lugar de la foto.
export const FOTOS = {
  catedral: { lugar: 'Catedral de Puebla', autor: 'Diego Delso', licencia: 'CC BY-SA 3.0', pagina: 'https://commons.wikimedia.org/wiki/File:Catedral_de_Puebla,_M%C3%A9xico,_2013-10-11,_DD_13.JPG' },
  capilla_rosario: { lugar: 'Capilla del Rosario (Templo de Santo Domingo)', autor: 'Fromaage', licencia: 'CC BY-SA 4.0', pagina: 'https://commons.wikimedia.org/wiki/File:Capilla_del_Rosario_Puebla_Diciembre_2015.jpg' },
  palafoxiana: { lugar: 'Biblioteca Palafoxiana', autor: 'ProtoplasmaKid', licencia: 'CC BY-SA 4.0', pagina: 'https://commons.wikimedia.org/wiki/File:Biblioteca_Palafoxiana_de_Puebla.jpg' },
  museo_amparo: { lugar: 'Museo Amparo', autor: 'MuseoAmparo', licencia: 'CC BY-SA 3.0', pagina: 'https://commons.wikimedia.org/wiki/File:Fachada_Museo_Amparo.jpg' },
  callejon_sapos: { lugar: 'Callejón de los Sapos', autor: 'Gusvel', licencia: 'CC BY-SA 4.0', pagina: 'https://commons.wikimedia.org/wiki/File:Callej%C3%B3n_de_los_sapos.JPG' },
  barrio_artista: { lugar: 'Barrio del Artista y El Parián', autor: 'Adrián Cerón', licencia: 'CC BY-SA 4.0', pagina: 'https://commons.wikimedia.org/wiki/File:Barrio_del_artista_en_Puebla.JPG' },
  casa_alfenique: { lugar: 'Casa del Alfeñique', autor: 'Mexch', licencia: 'CC BY-SA 3.0', pagina: 'https://commons.wikimedia.org/wiki/File:Casa_Alfe%C3%B1ique.JPG' },
  barrio_xanenetla: { lugar: 'Barrio de Xanenetla', autor: 'CUTI1', licencia: 'CC BY-SA 3.0', pagina: 'https://commons.wikimedia.org/wiki/File:Templo_de_Santa_In%C3%A9s,_Puebla.jpg' },
  fuertes: { lugar: 'Zona de los Fuertes (Loreto y Guadalupe)', autor: 'Comisión Mexicana de Filmaciones from México D. F., México', licencia: 'CC BY-SA 2.0', pagina: 'https://commons.wikimedia.org/wiki/File:Fuerte_De_Loreto,_Puebla_(33155109962).jpg' },
  museo_barroco: { lugar: 'Museo Internacional del Barroco', autor: 'CUTI1', licencia: 'CC BY-SA 4.0', pagina: 'https://commons.wikimedia.org/wiki/File:Museo_Internacional_del_Barroco.jpg' },
  estrella_puebla: { lugar: 'Estrella de Puebla', autor: 'Juan Carlos Fonseca Mata', licencia: 'CC BY-SA 4.0', pagina: 'https://commons.wikimedia.org/wiki/File:Estrella_de_Puebla_y_Letrero.jpg' },
  zona_arq_cholula: { lugar: 'Zona Arqueológica de Cholula (Gran Pirámide)', autor: 'Diego Delso', licencia: 'CC BY-SA 3.0', pagina: 'https://commons.wikimedia.org/wiki/File:Gran_Pir%C3%A1mide_de_Cholula,_Puebla,_M%C3%A9xico,_2013-10-12,_DD_14.JPG' },
  remedios: { lugar: 'Santuario de la Virgen de los Remedios', autor: 'Diego Delso', licencia: 'CC BY-SA 3.0', pagina: 'https://commons.wikimedia.org/wiki/File:Nuestra_Se%C3%B1ora_de_los_Remedios,_Cholula,_Puebla,_M%C3%A9xico,_2013-10-12,_DD_05.JPG' },
  san_gabriel: { lugar: 'Exconvento de San Gabriel y Capilla Real', autor: 'Koffermejia', licencia: 'CC BY-SA 4.0', pagina: 'https://commons.wikimedia.org/wiki/File:Fachada_Convento_de_San_Gabriel_Arc%C3%A1ngel.jpg' },
  tonantzintla: { lugar: 'Santa María Tonantzintla', autor: 'Carmelita Thierry', licencia: 'CC BY-SA 3.0', pagina: 'https://commons.wikimedia.org/wiki/File:Templo_de_Santa_Mar%C3%ADa_Tonantzintla.jpg' },
  acatepec: { lugar: 'San Francisco Acatepec', autor: 'Luisalvaz', licencia: 'CC BY-SA 4.0', pagina: 'https://commons.wikimedia.org/wiki/File:Fachada_del_Templo_de_San_Francisco_Acatepec_01.jpg' },
  huejotzingo: { lugar: 'Exconvento de Huejotzingo', autor: 'Luisalvaz', licencia: 'CC0 (dominio público)', pagina: 'https://commons.wikimedia.org/wiki/File:Templo_y_exconvento_de_San_Miguel_Arc%C3%A1ngel,_Huejotzingo,_desde_un_dron_32.png' },
  atlixco_centro: { lugar: 'Centro de Atlixco', autor: 'Adam Jones from Kelowna, BC, Canada', licencia: 'CC BY-SA 2.0', pagina: 'https://commons.wikimedia.org/wiki/File:Zocalo_Scene_with_Cathedral_Backdrop_-_Atlixco_-_Puebla_-_Mexico_(20447408845).jpg' },
  cerro_san_miguel: { lugar: 'Cerro de San Miguel', autor: 'Boriselmagnifico', licencia: 'CC BY-SA 3.0', pagina: 'https://commons.wikimedia.org/wiki/File:QUE_PANORAMICA_DEL_CERRITO_DE_SANMIGUEL.JPG' },
  africam: { lugar: 'Africam Safari', autor: 'Mamj16', licencia: 'CC0 (dominio público)', pagina: 'https://commons.wikimedia.org/wiki/File:Grants_zebras_zoo.jpg' },
  zocalo_puebla: { lugar: 'Zócalo de Puebla', autor: 'Luis Alvaz', licencia: 'CC BY-SA 4.0', pagina: 'https://commons.wikimedia.org/wiki/File:Z%C3%B3calo_de_Puebla_01.jpg' },
  casa_serdan: { lugar: 'Museo Casa de los Hermanos Serdán', autor: 'Luis Alvaz', licencia: 'CC BY-SA 4.0', pagina: 'https://commons.wikimedia.org/wiki/File:Fachada_de_la_Casa_de_los_Hermanos_Serd%C3%A1n_(Museo_de_la_Revoluci%C3%B3n)_01.jpg' },
  acuario_michin: { lugar: 'Acuario Michin Puebla', autor: 'Axel3733', licencia: 'CC BY-SA 4.0', pagina: 'https://commons.wikimedia.org/wiki/File:Acuario_michin.jpg' },
}

export function rutaFoto(id, tamano = 'grande') {
  return `${import.meta.env.BASE_URL}fotos/${id}${tamano === 'mini' ? '-mini' : ''}.jpg`
}
