package com.ferreteria.pedido;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebChromeClient;
import java.io.*;

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
        if (android.os.Build.VERSION.SDK_INT >= 16) {
            settings.setAllowFileAccessFromFileURLs(true);
            settings.setAllowUniversalAccessFromFileURLs(true);
        }
        settings.setMediaPlaybackRequiresUserGesture(false);

        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient());

        copyAssets("www", getFilesDir().getAbsolutePath());

        webView.loadUrl("file://" + getFilesDir() + "/www/index.html");
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
