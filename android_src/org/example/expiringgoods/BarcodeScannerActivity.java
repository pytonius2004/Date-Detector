package org.example.expiringgoods;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.ComponentActivity;
import androidx.annotation.NonNull;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageAnalysis;
import androidx.camera.core.ImageProxy;
import androidx.camera.core.Preview;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.view.PreviewView;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.google.common.util.concurrent.ListenableFuture;

import com.google.mlkit.vision.barcode.BarcodeScanner;
import com.google.mlkit.vision.barcode.BarcodeScannerOptions;
import com.google.mlkit.vision.barcode.BarcodeScanning;
import com.google.mlkit.vision.barcode.common.Barcode;

import com.google.mlkit.vision.common.InputImage;

import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;


/**
 * Нативный Android-сканер.
 *
 * CameraX:
 *   изображение камеры.
 *
 * Google ML Kit:
 *   распознавание штрихкода.
 *
 * Результат возвращается в PythonActivity:
 *
 *     barcode = "123456789..."
 *
 * либо:
 *
 *     manual = true
 *
 * если пользователь нажал
 * "Добавить вручную".
 */
public class BarcodeScannerActivity
        extends ComponentActivity {

    private static final int CAMERA_PERMISSION_REQUEST =
            6001;


    private PreviewView previewView;

    private TextView instructionText;

    private Button manualButton;


    private ExecutorService cameraExecutor;

    private BarcodeScanner barcodeScanner;


    private final AtomicBoolean resultSent =
            new AtomicBoolean(false);


    private int dp(float value) {

        return Math.round(
                value
                        *
                        getResources()
                                .getDisplayMetrics()
                                .density
        );
    }


    @Override
    protected void onCreate(
            Bundle savedInstanceState
    ) {

        super.onCreate(
                savedInstanceState
        );


        // -------------------------------------------------
        // ROOT
        // -------------------------------------------------

        FrameLayout root =
                new FrameLayout(this);


        // -------------------------------------------------
        // CAMERA PREVIEW
        // -------------------------------------------------

        previewView =
                new PreviewView(this);

        previewView.setImplementationMode(
                PreviewView
                        .ImplementationMode
                        .COMPATIBLE
        );


        FrameLayout.LayoutParams previewParams =
                new FrameLayout.LayoutParams(
                        FrameLayout.LayoutParams.MATCH_PARENT,
                        FrameLayout.LayoutParams.MATCH_PARENT
                );

        root.addView(
                previewView,
                previewParams
        );


        // -------------------------------------------------
        // TOP TEXT
        // -------------------------------------------------

        instructionText =
                new TextView(this);

        instructionText.setText(
                "Наведите камеру на штрихкод"
        );

        instructionText.setTextColor(
                Color.WHITE
        );

        instructionText.setTextSize(
                20
        );

        instructionText.setGravity(
                Gravity.CENTER
        );

        instructionText.setPadding(
                dp(12),
                dp(12),
                dp(12),
                dp(12)
        );

        instructionText.setBackgroundColor(
                Color.argb(
                        180,
                        20,
                        20,
                        20
                )
        );


        FrameLayout.LayoutParams instructionParams =
                new FrameLayout.LayoutParams(
                        FrameLayout.LayoutParams.MATCH_PARENT,
                        FrameLayout.LayoutParams.WRAP_CONTENT
                );

        instructionParams.gravity =
                Gravity.TOP;

        instructionParams.leftMargin =
                dp(12);

        instructionParams.rightMargin =
                dp(12);

        root.addView(
                instructionText,
                instructionParams
        );


        // -------------------------------------------------
        // MANUAL BUTTON
        // -------------------------------------------------

        manualButton =
                new Button(this);

        manualButton.setText(
                "Добавить вручную"
        );

        manualButton.setTextSize(
                18
        );

        manualButton.setAllCaps(
                false
        );


        FrameLayout.LayoutParams manualParams =
                new FrameLayout.LayoutParams(
                        FrameLayout.LayoutParams.MATCH_PARENT,
                        dp(64)
                );

        manualParams.gravity =
                Gravity.BOTTOM;

        manualParams.leftMargin =
                dp(16);

        manualParams.rightMargin =
                dp(16);

        root.addView(
                manualButton,
                manualParams
        );


        manualButton.setOnClickListener(
                view -> returnManual()
        );


        // -------------------------------------------------
        // SYSTEM SAFE AREA
        // -------------------------------------------------
        //
        // Камера может рисоваться под системными панелями,
        // это нормально.
        //
        // А надпись и кнопка должны находиться ВНУТРИ
        // безопасной области.
        // -------------------------------------------------

        root.setOnApplyWindowInsetsListener(
                (view, insets) -> {

                    int topInset =
                            insets.getSystemWindowInsetTop();

                    int bottomInset =
                            insets.getSystemWindowInsetBottom();


                    FrameLayout.LayoutParams topParams =
                            (FrameLayout.LayoutParams)
                                    instructionText
                                            .getLayoutParams();

                    topParams.topMargin =
                            topInset
                                    +
                                    dp(12);

                    topParams.leftMargin =
                            dp(12);

                    topParams.rightMargin =
                            dp(12);

                    instructionText.setLayoutParams(
                            topParams
                    );


                    FrameLayout.LayoutParams bottomParams =
                            (FrameLayout.LayoutParams)
                                    manualButton
                                            .getLayoutParams();

                    bottomParams.bottomMargin =
                            bottomInset
                                    +
                                    dp(14);

                    bottomParams.leftMargin =
                            dp(16);

                    bottomParams.rightMargin =
                            dp(16);

                    manualButton.setLayoutParams(
                            bottomParams
                    );


                    return insets;
                }
        );


        setContentView(
                root
        );


        root.requestApplyInsets();


        // -------------------------------------------------
        // ML KIT
        // -------------------------------------------------

        cameraExecutor =
                Executors.newSingleThreadExecutor();


        BarcodeScannerOptions options =
                new BarcodeScannerOptions
                        .Builder()

                        .setBarcodeFormats(

                                Barcode.FORMAT_EAN_13,

                                Barcode.FORMAT_EAN_8,

                                Barcode.FORMAT_UPC_A,

                                Barcode.FORMAT_UPC_E,

                                Barcode.FORMAT_CODE_128,

                                Barcode.FORMAT_CODE_39,

                                Barcode.FORMAT_ITF
                        )

                        .build();


        barcodeScanner =
                BarcodeScanning.getClient(
                        options
                );


        // -------------------------------------------------
        // CAMERA PERMISSION
        // -------------------------------------------------

        if (
                ContextCompat.checkSelfPermission(
                        this,
                        Manifest.permission.CAMERA
                )
                        ==
                        PackageManager.PERMISSION_GRANTED
        ) {

            startCamera();

        } else {

            ActivityCompat.requestPermissions(

                    this,

                    new String[]{
                            Manifest.permission.CAMERA
                    },

                    CAMERA_PERMISSION_REQUEST
            );
        }
    }


    // =====================================================
    // CAMERA PERMISSION RESULT
    // =====================================================

    @Override
    public void onRequestPermissionsResult(

            int requestCode,

            @NonNull
            String[] permissions,

            @NonNull
            int[] grantResults
    ) {

        super.onRequestPermissionsResult(
                requestCode,
                permissions,
                grantResults
        );


        if (
                requestCode
                        ==
                        CAMERA_PERMISSION_REQUEST
        ) {

            if (
                    grantResults.length
                            >
                            0

                            &&

                            grantResults[0]
                                    ==
                                    PackageManager.PERMISSION_GRANTED
            ) {

                startCamera();

            } else {

                Toast.makeText(

                        this,

                        "Разрешение камеры не предоставлено",

                        Toast.LENGTH_LONG

                ).show();


                finish();
            }
        }
    }


    // =====================================================
    // START CAMERA
    // =====================================================

    private void startCamera() {

        ListenableFuture<ProcessCameraProvider>
                cameraProviderFuture =

                ProcessCameraProvider
                        .getInstance(
                                this
                        );


        cameraProviderFuture.addListener(

                () -> {

                    try {

                        ProcessCameraProvider
                                cameraProvider =

                                cameraProviderFuture
                                        .get();


                        // -------------------------------
                        // Preview
                        // -------------------------------

                        Preview preview =
                                new Preview
                                        .Builder()
                                        .build();


                        preview.setSurfaceProvider(
                                previewView
                                        .getSurfaceProvider()
                        );


                        // -------------------------------
                        // Image analysis
                        // -------------------------------

                        ImageAnalysis imageAnalysis =
                                new ImageAnalysis
                                        .Builder()

                                        .setBackpressureStrategy(
                                                ImageAnalysis
                                                        .STRATEGY_KEEP_ONLY_LATEST
                                        )

                                        .build();


                        imageAnalysis.setAnalyzer(

                                cameraExecutor,

                                this::analyzeFrame
                        );


                        CameraSelector cameraSelector =
                                CameraSelector
                                        .DEFAULT_BACK_CAMERA;


                        cameraProvider.unbindAll();


                        cameraProvider.bindToLifecycle(

                                this,

                                cameraSelector,

                                preview,

                                imageAnalysis
                        );


                    } catch (
                            ExecutionException
                                    |
                                    InterruptedException e
                    ) {

                        Toast.makeText(

                                this,

                                "Не удалось запустить камеру: "
                                        +
                                        e.getMessage(),

                                Toast.LENGTH_LONG

                        ).show();


                        finish();
                    }

                },

                ContextCompat.getMainExecutor(
                        this
                )
        );
    }


    // =====================================================
    // ANALYZE CAMERA FRAME
    // =====================================================

    private void analyzeFrame(
            @NonNull
            ImageProxy imageProxy
    ) {

        if (
                resultSent.get()
        ) {

            imageProxy.close();

            return;
        }


        if (
                imageProxy.getImage()
                        ==
                        null
        ) {

            imageProxy.close();

            return;
        }


        InputImage image =
                InputImage.fromMediaImage(

                        imageProxy.getImage(),

                        imageProxy
                                .getImageInfo()
                                .getRotationDegrees()
                );


        barcodeScanner
                .process(
                        image
                )

                .addOnSuccessListener(

                        barcodes -> {

                            if (
                                    resultSent.get()
                            ) {

                                return;
                            }


                            for (
                                    Barcode barcode
                                    :
                                    barcodes
                            ) {

                                String rawValue =
                                        barcode
                                                .getRawValue();


                                if (
                                        rawValue
                                                !=
                                                null

                                                &&

                                                !rawValue
                                                        .trim()
                                                        .isEmpty()
                                ) {

                                    if (
                                            resultSent
                                                    .compareAndSet(
                                                            false,
                                                            true
                                                    )
                                    ) {

                                        returnBarcode(
                                                rawValue
                                                        .trim()
                                        );
                                    }

                                    break;
                                }
                            }
                        }
                )

                .addOnFailureListener(

                        exception -> {

                            // Ошибка отдельного кадра
                            // не должна закрывать камеру.
                        }
                )

                .addOnCompleteListener(

                        task ->
                                imageProxy.close()
                );
    }


    // =====================================================
    // RETURN BARCODE
    // =====================================================

    private void returnBarcode(
            String barcode
    ) {

        Intent result =
                new Intent();


        result.putExtra(
                "barcode",
                barcode
        );


        result.putExtra(
                "manual",
                false
        );


        setResult(
                RESULT_OK,
                result
        );


        finish();
    }


    // =====================================================
    // MANUAL ENTRY
    // =====================================================

    private void returnManual() {

        if (
                !resultSent.compareAndSet(
                        false,
                        true
                )
        ) {

            return;
        }


        Intent result =
                new Intent();


        result.putExtra(
                "manual",
                true
        );


        setResult(
                RESULT_OK,
                result
        );


        finish();
    }


    // =====================================================
    // DESTROY
    // =====================================================

    @Override
    protected void onDestroy() {

        super.onDestroy();


        if (
                barcodeScanner
                        !=
                        null
        ) {

            barcodeScanner.close();
        }


        if (
                cameraExecutor
                        !=
                        null
        ) {

            cameraExecutor.shutdown();
        }
    }
}
