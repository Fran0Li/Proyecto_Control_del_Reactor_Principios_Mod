# Audio del juego (US-29)

| Archivo | Qué es | Dónde suena |
| --- | --- | --- |
| `musica_partida.ogg` | Los primeros 40 s de "Reactors at Critical", en bucle (con un fundido corto al final para que el corte no se note) | En la arena, desde que se entra hasta que se sale |

"Reactors at Critical" es una pista instrumental creada por Francisco Li para el proyecto con
Suno. Se recortó y se pasó a OGG (el formato que mejor carga pygbag en el navegador) con:

```
ffmpeg -i Reactors_at_Critical.mp3 -t 40 -vn -af "afade=t=in:st=0:d=0.05,afade=t=out:st=39.2:d=0.8" -ac 2 -ar 44100 -c:a libvorbis -q:a 3 musica_partida.ogg
```

Los efectos (extracción, bolita de energía, golpe de guardián y evento especial) no son archivos:
se generan en código en `src/sonidos.py`. En la arena, la tecla **M** silencia la música y los
efectos.
