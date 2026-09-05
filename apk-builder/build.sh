#!/data/data/com.termux/files/usr/bin/bash
set -e

PROJECT="${1:-ferreteria}"
PKG="com.ferreteria.pedido"
BUILD="build"
OUT="."
ANDROID_HOME="$HOME/android-sdk"
PLATFORM="$ANDROID_HOME/platforms/android-34/android.jar"

if [ -z "$1" ]; then
    echo "Uso: ./build.sh [nombre_proyecto]"
    echo "Ejemplo: ./build.sh ferreteria"
    exit 1
fi

if [ ! -d "$PROJECT" ]; then
    echo "Error: Directorio '$PROJECT' no encontrado"
    exit 1
fi

if [ ! -f "$PLATFORM" ]; then
    echo "Error: android.jar no encontrado en $PLATFORM"
    echo "Ejecuta: yes | sdkmanager --install 'platforms;android-34'"
    exit 1
fi

echo "=== Construyendo APK: $PROJECT ==="

# Limpiar build anterior
rm -rf $BUILD
mkdir -p $BUILD/classes

# 0. Generar R.java
echo "[0/8] Generando R.java..."
aapt package -f -m \
    -S $PROJECT/res \
    -M $PROJECT/AndroidManifest.xml \
    -I "$PLATFORM" \
    -J $BUILD \
    -F $BUILD/resources.apk

# 1. Java → .class (incluyendo R.java)
echo "[1/8] Compilando Java..."
javac --release 8 -d $BUILD/classes \
    -classpath "$PLATFORM" \
    -sourcepath $PROJECT/src:$BUILD \
    $PROJECT/src/com/ferreteria/pedido/*.java \
    $BUILD/com/ferreteria/pedido/R.java

# 2. .class → .jar
echo "[2/8] Empaquetando JAR..."
jar cvf $BUILD/classes.jar -C $BUILD/classes . 2>/dev/null

# 3. .jar → .dex
echo "[3/8] Convirtiendo a DEX..."
d8 --min-api 26 --output $BUILD/ $BUILD/classes.jar

# 4. Empaquetar recursos (sin -J porque ya tenemos R.java)
echo "[4/8] Empaquetando recursos..."
rm -f $BUILD/resources.apk
aapt package -f \
    -S $PROJECT/res \
    -M $PROJECT/AndroidManifest.xml \
    -I "$PLATFORM" \
    -F $BUILD/base.apk

# 5. Agregar DEX al APK
echo "[5/8] Agregando DEX..."
cd $BUILD
aapt add base.apk classes.dex
cd ..

# 6. Agregar assets (www/)
echo "[6/8] Agregando assets..."
cd $PROJECT
find assets/www -type f | while read f; do
    aapt add "$OLDPWD/$BUILD/base.apk" "$f" 2>/dev/null || true
done
cd "$OLDPWD"

# 7. Firmar
echo "[7/8] Firmando APK..."
KEYSTORE=~/.apk-builder-debug.keystore
if [ ! -f "$KEYSTORE" ]; then
    echo "Generando keystore de debug..."
    keytool -genkey -v -keystore $KEYSTORE \
        -alias androiddebugkey \
        -keyalg RSA -keysize 2048 -validity 10000 \
        -storepass android -keypass android \
        -dname "CN=Android Debug,O=Android,C=US"
fi

cp $BUILD/base.apk $OUT/$PROJECT-app-unsigned.apk
apksigner sign --ks $KEYSTORE \
    --ks-pass pass:android \
    --key-pass pass:android \
    --ks-key-alias androiddebugkey \
    $OUT/$PROJECT-app-unsigned.apk

mv $OUT/$PROJECT-app-unsigned.apk $OUT/$PROJECT-app.apk

# Limpiar
rm -rf $BUILD

echo ""
echo "=== APK generado: $OUT/$PROJECT-app.apk ==="
echo "Tamano: $(du -h $OUT/$PROJECT-app.apk | cut -f1)"
echo ""
echo "Para instalar:"
echo "  adb install -r $OUT/$PROJECT-app.apk"
echo "  adb shell am start -n $PKG/.MainActivity"
