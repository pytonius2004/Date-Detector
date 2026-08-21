package org.example.expiringgoods;

import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

public final class DatabaseExportHelper {

    private DatabaseExportHelper() {
    }

    /**
     * Экспортирует SQLite БД приложения
     * непосредственно в публичную папку Downloads.
     *
     * @param context    Android Context / Activity
     * @param sourcePath путь к временной БД приложения
     * @param fileName   имя выходного файла
     * @return имя сохранённого файла
     */
    public static String exportToDownloads(
            Context context,
            String sourcePath,
            String fileName
    ) throws Exception {

        File sourceFile = new File(sourcePath);

        if (!sourceFile.exists()) {
            throw new Exception(
                    "Исходный файл БД не найден: " + sourcePath
            );
        }

        if (!sourceFile.isFile()) {
            throw new Exception(
                    "Путь БД не является файлом: " + sourcePath
            );
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            return exportUsingMediaStore(
                    context,
                    sourceFile,
                    fileName
            );
        }

        return exportLegacy(
                sourceFile,
                fileName
        );
    }

    /**
     * Android 10+.
     *
     * Используем MediaStore, поэтому никакого разрешения
     * на доступ ко всему хранилищу не требуется.
     */
    private static String exportUsingMediaStore(
            Context context,
            File sourceFile,
            String fileName
    ) throws Exception {

        ContentResolver resolver =
                context.getContentResolver();

        ContentValues values =
                new ContentValues();

        values.put(
                MediaStore.MediaColumns.DISPLAY_NAME,
                fileName
        );

        values.put(
                MediaStore.MediaColumns.MIME_TYPE,
                "application/octet-stream"
        );

        values.put(
                MediaStore.MediaColumns.RELATIVE_PATH,
                Environment.DIRECTORY_DOWNLOADS
        );

        Uri collection =
                MediaStore.Downloads.EXTERNAL_CONTENT_URI;

        Uri uri = resolver.insert(
                collection,
                values
        );

        if (uri == null) {
            throw new Exception(
                    "Android не смог создать файл в Downloads."
            );
        }

        boolean success = false;

        try (
                InputStream inputStream =
                        new FileInputStream(sourceFile);

                OutputStream outputStream =
                        resolver.openOutputStream(uri)
        ) {

            if (outputStream == null) {
                throw new Exception(
                        "Android не смог открыть файл Downloads для записи."
                );
            }

            byte[] buffer = new byte[16 * 1024];

            int read;

            while (
                    (read = inputStream.read(buffer))
                            != -1
            ) {

                outputStream.write(
                        buffer,
                        0,
                        read
                );
            }

            outputStream.flush();

            success = true;

        } finally {

            if (!success) {

                try {
                    resolver.delete(
                            uri,
                            null,
                            null
                    );
                } catch (Exception ignored) {
                }
            }
        }

        return fileName;
    }

    /**
     * Старые Android.
     *
     * Для современных Android этот код вообще
     * использоваться не будет.
     */
    private static String exportLegacy(
            File sourceFile,
            String fileName
    ) throws Exception {

        File downloads =
                Environment.getExternalStoragePublicDirectory(
                        Environment.DIRECTORY_DOWNLOADS
                );

        if (!downloads.exists()) {

            if (!downloads.mkdirs()) {

                throw new Exception(
                        "Не удалось создать папку Downloads."
                );
            }
        }

        File destination =
                new File(
                        downloads,
                        fileName
                );

        try (
                InputStream inputStream =
                        new FileInputStream(sourceFile);

                OutputStream outputStream =
                        new FileOutputStream(destination)
        ) {

            byte[] buffer =
                    new byte[16 * 1024];

            int read;

            while (
                    (read = inputStream.read(buffer))
                            != -1
            ) {

                outputStream.write(
                        buffer,
                        0,
                        read
                );
            }

            outputStream.flush();
        }

        return destination.getAbsolutePath();
    }
}
