# Despliegue en OCI Compute con Portainer

Guía para levantar FinanceAI en una instancia de OCI Compute que ya tiene Docker, Portainer y
nginx-proxy-manager.

Con esto queda cubierto el requisito del reto **"OCI Compute para el alojamiento de la
aplicación"**.

---

## Antes de empezar

Comprueba desde el servidor que efectivamente es una instancia de OCI:

```bash
curl -s -H "Authorization: Bearer Oracle" \
  http://169.254.169.254/opc/v2/instance/ | head -20
```

Ese endpoint de metadatos solo responde dentro de OCI. Si devuelve JSON con `shape`,
`region` y `compartmentId`, estás en OCI. Guarda esa salida: sirve como evidencia para la
entrega.

### Puertos

FinanceAI publica **8080** (API) y **8081** (frontend). El ml-service **no publica puerto**:
solo es accesible desde la red interna del stack.

Si ya tienes algo en esos puertos, cámbialos con las variables `PUERTO_API` y `PUERTO_WEB`
al crear el stack.

> El `8000` estaba ocupado por Portainer. Por eso el ml-service dejó de publicarlo.

Abre 8080 y 8081 en dos sitios, o no habrá acceso desde fuera:

1. **Security List / NSG de la subred**, en la consola de OCI: *Networking → VCN → Subnet →
   Security List → Add Ingress Rules*, origen `0.0.0.0/0`, TCP, puertos 8080 y 8081.
2. **Firewall de la instancia.** Oracle Linux trae `firewalld` activo:

```bash
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --permanent --add-port=8081/tcp
sudo firewall-cmd --reload
```

En Ubuntu, si `iptables` tiene las reglas por defecto de Oracle:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8080 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8081 -j ACCEPT
sudo netfilter-persistent save
```

---

## Desplegar con Portainer

El repositorio es público, así que no hacen falta credenciales.

1. Portainer → **Stacks** → **Add stack**
2. Nombre: `financeai`
3. Método de build: **Repository**
4. Rellena:

   | Campo | Valor |
   |---|---|
   | Repository URL | `https://github.com/No-Country-simulation/G9-LATAM-TEAM-44-FinanceAI` |
   | Repository reference | `refs/heads/Eglis-Full-Stack-Developer` |
   | Compose path | `docker-compose.yml` |

5. (Opcional) En **Environment variables**, si necesitas cambiar puertos o activar OCI
   Object Storage:

   | Variable | Ejemplo |
   |---|---|
   | `PUERTO_API` | `8080` |
   | `PUERTO_WEB` | `8081` |
   | `OCI_PAR_URL` | `https://objectstorage.<region>.oraclecloud.com/p/.../o/` |
   | `OCI_BUCKET` | `finance-ai-models` |
   | `OCI_NAMESPACE` | tu namespace |
   | `OCI_REGION` | `us-ashburn-1` |

6. **Deploy the stack**

El primer despliegue tarda. La imagen de Java compila el proyecto con Maven dentro del
contenedor y descarga las dependencias: entre 3 y 10 minutos según la instancia.

### Comprobar que arrancó

```bash
curl http://<IP-de-la-instancia>:8080/api/v1/health
curl http://<IP-de-la-instancia>:8080/api/v1/ml-status
```

En `ml-status`, `disponible: true` y `modelo.origen` en `local` u `oci` significa que todo
está conectado. Después, abre `http://<IP>:8081` en el navegador.

Para la prueba completa, desde tu equipo:

```bash
python docs/ejemplos.py http://<IP-de-la-instancia>:8080
```

---

## Dominio y HTTPS con nginx-proxy-manager

Ya tienes NPM corriendo, así que en lugar de exponer puertos sueltos conviene darle un
dominio con certificado.

**Frontend** — *Proxy Hosts → Add Proxy Host*:

| Campo | Valor |
|---|---|
| Domain Names | `financeai.tudominio.com` |
| Scheme | `http` |
| Forward Hostname / IP | `financeai-web` |
| Forward Port | `80` |
| Block Common Exploits | activado |
| Websockets Support | activado |

En la pestaña **SSL**: *Request a new SSL Certificate*, con *Force SSL* y *HTTP/2*.

Como el contenedor `financeai-web` ya hace de proxy hacia la API en `/api/`, **con este
único proxy host es suficiente**: el frontend y la API quedan bajo el mismo dominio y no hay
CORS que configurar.

### Importante: la red de Docker

NPM solo puede resolver `financeai-web` por nombre si ambos contenedores comparten red. Si
NPM está en otra red, conéctalo:

```bash
docker network ls | grep financeai
docker network connect <red-de-financeai> nginx-proxy-manager
```

La alternativa, si prefieres no tocar redes, es usar la IP interna del host y el puerto
publicado: Forward Hostname `172.17.0.1`, Forward Port `8081`.

---

## Actualizar tras un cambio en GitHub

Portainer → Stacks → `financeai` → **Pull and redeploy**. Marca *Re-pull image and redeploy*
para que reconstruya con el último commit.

Desde la terminal:

```bash
cd /ruta/al/repo
git pull
docker compose up -d --build
```

---

## Si algo falla

| Síntoma | Causa probable |
|---|---|
| El stack no arranca, error de puerto en uso | Otro contenedor ocupa 8080 u 8081. Cámbialos con `PUERTO_API` / `PUERTO_WEB` |
| La build de Java se queda colgada o muere | Falta memoria. Ver más abajo |
| `ml-status` dice `disponible: false` | El ml-service no arrancó. Mira sus logs: `docker logs financeai-ml` |
| `modelo.origen: "reglas"` | No encontró los artefactos. Van dentro de la imagen, así que reconstruye sin caché: *Pull and redeploy* con *Re-pull image* marcado |
| El frontend carga pero no analiza | Abre la consola del navegador. Si hay error de CORS, revisa que estés entrando por el frontend y no directamente a la API |
| No responde desde fuera | Falta abrir el puerto en la Security List de OCI **y** en el firewall de la instancia. Son dos cosas distintas |

### Si la instancia tiene poca memoria

La imagen de Java compila con Maven dentro del contenedor. En una instancia pequeña
(1 GB, como la `VM.Standard.E2.1.Micro`) eso puede agotar la RAM.

Dos salidas:

**Añadir swap**, que suele bastar:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

**O construir el jar fuera y copiarlo**, evitando compilar en el servidor:

```bash
# en tu equipo
cd srv-java && ./mvnw package -DskipTests
scp target/*.jar usuario@servidor:/ruta/
```

Si vas por esta vía, el `Dockerfile` de `srv-java` necesita un ajuste para partir del jar ya
construido en lugar de compilarlo. Dilo y lo preparo.

---

## Nota sobre los volúmenes en stacks de Git

Los modelos entrenados viajan **dentro de la imagen** del ml-service, no montados como
volumen.

El motivo es concreto: Portainer clona el repositorio en su propio contenedor
(`/data/compose/<id>`), pero los bind mounts los resuelve el daemon de Docker en el **host**.
Una ruta relativa como `./ciencia-datos/artefactos` apunta entonces a un directorio que no
existe en el host, Docker lo crea vacío y el servicio arranca sin modelos, con
`origen: "reglas"`.

Con los artefactos dentro de la imagen esto no puede pasar. Si configuras Object Storage,
`OCI_PAR_URL` sigue teniendo prioridad y los de la imagen quedan como respaldo.

---

## Qué queda cubierto del reto

| Requisito | Cómo |
|---|---|
| **OCI Compute** para el alojamiento | Los tres contenedores corriendo en la instancia |
| **OCI Object Storage** (opcional aquí) | Configurando `OCI_PAR_URL`. Ver [OCI.md](OCI.md) |

Para la entrega, guarda:

- La salida del endpoint de metadatos (`169.254.169.254`), que prueba que es OCI.
- Una captura de Portainer con los tres contenedores en verde.
- La URL pública funcionando.
