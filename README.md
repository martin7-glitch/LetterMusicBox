## LetterMusicBox
# Catalogo de Musica

## Ejecutar la aplicación

1. Instala las dependencias con `python -m pip install -r requirements.txt`.
2. Inicia MongoDB local.
3. Ejecuta `python main.py`.

Las portadas elegidas se copian a la carpeta `covers/`; MongoDB guarda la ruta de cada imagen junto a la canción. Esa carpeta contiene archivos locales y no se incluye en Git.

## Ejecutar la versión web

1. Instala las dependencias con `python -m pip install -r requirements.txt`.
2. Inicia MongoDB local.
3. Ejecuta `python webapp.py`.
4. Abre <http://127.0.0.1:5000> en el navegador.

La versión web usa la base `lettermusicbox` y colección `canciones`. Cada visitante debe crear una cuenta e iniciar sesión. La biblioteca personal solo muestra y modifica canciones asociadas a esa cuenta; la pestaña **Miembros** permite consultar perfiles y canciones de otros usuarios registrados, incluidas sus portadas, calificaciones y Logs. Los usuarios no se repiten (ignorando mayúsculas/minúsculas) y las contraseñas se guardan hasheadas. Los registros anteriores, que no tienen propietario, no se muestran en la web. `page.py` es la aplicación de escritorio y no usa estas cuentas.

Las portadas se guardan en `imagenes_canciones/` en el servidor y no se incluyen en Git. Por defecto, el servidor solo escucha en tu computadora. Para publicarla en internet hace falta desplegar el backend y configurar una base de datos accesible desde ese servidor; no publiques MongoDB directamente. Puedes configurar la conexión con la variable de entorno `MONGODB_URI`.

### Desplegar en Render

Configura el servicio web con estos comandos:

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn --bind 0.0.0.0:$PORT webapp:app`

En **Environment**, configura `MONGODB_URI` con la URI de una base MongoDB accesible desde Render y `SECRET_KEY` con un valor secreto estable para que las sesiones sigan funcionando tras reinicios. La app Flask se exporta como `app` en `webapp.py`.

_hola profe como anda? este es nuestro repositorio github_

_nuestro plan es hacer __LetterMusicBox__ asi que veamos como va_

Nuestras ideas son:

* _Agregar canciones_: se le permite al usuario registrar: nombre, artista, álbum, tipo (show, single, común, entre otros), imagen, puntuación, duración, calificación por edad, genero, año, y log (opcional).

* _Editar canciones_: se le permite al usuario editar la imagen, log y puntuación.

* _Eliminar canciones_: se le permite al usuario eliminar una canción de la lista (con verificación).

* _Sistema de filtro y búsqueda_: barra de búsqueda, filtro y tags de búsqueda (año, genero, etc).

* _Sistema de journal_: ver los logs que se escribieron junto a la fecha, ver en que fecha se agregaron las canciones a la aplicación.

_Cambios 23/10_

* _Agregamos el formulario_
* _Pulimos la interfaz_
* _Conectamos la base de datos_
* _Agregamos chicas anime_
* _Agregamos el sistema de busqueda por tags y por nombre_
* _Agregamos la tabla para visualizar el contenido de la base de datos_

_Cambios 26/10_
* _Agregamos la funcion de estrellas_
* _Agregamos el logo de la aplicacion_
* _reacomodamos ligeramente la interfaz_


![aca chicas anime](https://static.wikia.nocookie.net/megamitensei/images/9/95/P5_Futaba_Sakura.png/revision/latest?cb=20191016035405&path-prefix=es)

![aca chicas anime](https://static.wikia.nocookie.net/megamitensei/images/b/be/An_takamaki.png/revision/latest?cb=20190624190416&path-prefix=es)

![chicas anime](https://static.wikia.nocookie.net/megamitensei/images/7/77/P5_Haru_Okumura.png/revision/latest?cb=20191017203721&path-prefix=es)

![chicas anime](https://static.wikia.nocookie.net/megamitensei/images/a/af/P5_Makoto_Nijima.png/revision/latest/scale-to-width-down/175?cb=20190810035653&path-prefix=es)

![chicas anime](https://static.wikia.nocookie.net/megamitensei/images/c/c6/Persona_5_Royal_Kasumi.png/revision/latest?cb=20190424131819)

![chicas anime](https://static.wikia.nocookie.net/megamitensei/images/e/eb/P5_Tae_Takemi.png/revision/latest?cb=20161220150151)

![chicas anime](https://static.wikia.nocookie.net/megamitensei/images/4/43/Sadayo_Kawakami.png/revision/latest?cb=20161220030038)

![chicas anime](https://static.wikia.nocookie.net/megamitensei/images/6/63/Persona_5_Hero.png/revision/latest/scale-to-width-down/1000?cb=20240407105006)
