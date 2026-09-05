package com.ferreteria.pedido;

import android.Manifest;
import android.app.Activity;
import android.content.ContentValues;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import java.io.*;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {
    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        webView = findViewById(R.id.webview);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        if (Build.VERSION.SDK_INT >= 16) {
            settings.setAllowFileAccessFromFileURLs(true);
            settings.setAllowUniversalAccessFromFileURLs(true);
        }
        settings.setMediaPlaybackRequiresUserGesture(false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String scheme = request.getUrl().getScheme();
                if ("http".equals(scheme) || "https".equals(scheme)) {
                    Intent intent = new Intent(Intent.ACTION_VIEW, request.getUrl());
                    startActivity(intent);
                    return true;
                }
                return false;
            }
        });
        webView.setWebChromeClient(new WebChromeClient());
        webView.addJavascriptInterface(new AndroidInterface(), "Android");

        copyAssets("www", getFilesDir().getAbsolutePath());

        webView.loadUrl("file://" + getFilesDir() + "/www/index.html");
    }

    private class AndroidInterface {

        @JavascriptInterface
        public String downloadPedido(String fileName, String html) {
            try {
                byte[] bytes = html.getBytes(StandardCharsets.UTF_8);
                if (Build.VERSION.SDK_INT >= 29) {
                    return saveToMediaStore(fileName, bytes);
                }
                return saveToLegacyDownloads(fileName, bytes);
            } catch (Exception e) {
                e.printStackTrace();
                return "ERR|No se pudo guardar el archivo: " + e.getMessage();
            }
        }

        private String saveToMediaStore(String fileName, byte[] bytes) throws IOException {
            ContentValues values = new ContentValues();
            values.put(MediaStore.Downloads.DISPLAY_NAME, fileName);
            values.put(MediaStore.Downloads.MIME_TYPE, "text/html");
            values.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
            values.put(MediaStore.Downloads.IS_PENDING, 1);
            Uri uri = getContentResolver().insert(
                    MediaStore.Downloads.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY), values);
            if (uri == null) {
                return "ERR|No se pudo crear el archivo en Descargas";
            }
            OutputStream os = getContentResolver().openOutputStream(uri);
            os.write(bytes);
            os.close();
            values.clear();
            values.put(MediaStore.Downloads.IS_PENDING, 0);
            getContentResolver().update(uri, values, null, null);
            return "OK|Descargas/" + fileName + "|" + uri.toString();
        }

        private String saveToLegacyDownloads(String fileName, byte[] bytes) throws IOException {
            if (Build.VERSION.SDK_INT >= 23
                    && checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE)
                    != PackageManager.PERMISSION_GRANTED) {
                requestStoragePermission();
                return "ERR|Se necesita permiso de almacenamiento. Toca 'Descargar PDF' de nuevo y acepta el permiso.";
            }
            File dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
            if (dir == null) {
                return "ERR|Almacenamiento no disponible";
            }
            if (!dir.exists()) {
                dir.mkdirs();
            }
            File out = new File(dir, fileName);
            FileOutputStream fos = new FileOutputStream(out);
            fos.write(bytes);
            fos.close();
            return "OK|" + out.getAbsolutePath() + "|";
        }

        @JavascriptInterface
        public String openFile(String uri) {
            if (uri == null || uri.isEmpty()) {
                return "ERR|No se puede abrir el archivo en este dispositivo";
            }
            final Intent intent = new Intent(Intent.ACTION_VIEW);
            intent.setDataAndType(Uri.parse(uri), "text/html");
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    try {
                        startActivity(intent);
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
            });
            return "OK";
        }

        private void requestStoragePermission() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    requestPermissions(new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE}, 1001);
                }
            });
        }
    }

    private void copyAssets(String assetPath, String destPath) {
        try {
            String[] files = getAssets().list(assetPath);
            if (files == null || files.length == 0) {
                return;
            }

            File destDir = new File(destPath + "/" + assetPath);
            if (!destDir.exists()) {
                destDir.mkdirs();
            }

            for (String file : files) {
                String srcPath = assetPath + "/" + file;
                String dstPath = destPath + "/" + srcPath;

                try {
                    InputStream in = getAssets().open(srcPath);
                    File outFile = new File(dstPath);
                    boolean isDataFile = file.equals("index.html")
                            || file.equals("productos.js")
                            || file.equals("productos.json");
                    if (outFile.exists() && !isDataFile) {
                        continue;
                    }
                    OutputStream out = new FileOutputStream(outFile);
                    byte[] buffer = new byte[4096];
                    int read;
                    while ((read = in.read(buffer)) != -1) {
                        out.write(buffer, 0, read);
                    }
                    out.close();
                    in.close();
                } catch (IOException e) {
                    File subDir = new File(dstPath);
                    if (!subDir.exists()) {
                        subDir.mkdirs();
                    }
                    copyAssets(srcPath, destPath);
                }
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}