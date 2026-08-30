package org.example.expiringgoods;

import android.content.ContentResolver;
import android.content.Context;
import android.net.Uri;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

public final class DatabaseImportHelper {

    private DatabaseImportHelper() {
    }

    /** Копирует SAF-файл буфером, без медленных побайтовых JNI-вызовов. */
    public static String copyUriToFile(
            Context context,
            Uri uri,
            String destinationPath
    ) throws Exception {
        ContentResolver resolver = context.getContentResolver();
        File destination = new File(destinationPath);

        try (
                InputStream input = resolver.openInputStream(uri);
                OutputStream output = new FileOutputStream(destination)
        ) {
            if (input == null) {
                throw new Exception("Android не смог открыть выбранный файл.");
            }

            byte[] buffer = new byte[64 * 1024];
            int read;

            while ((read = input.read(buffer)) != -1) {
                output.write(buffer, 0, read);
            }

            output.flush();
        } catch (Exception error) {
            if (destination.exists()) {
                //noinspection ResultOfMethodCallIgnored
                destination.delete();
            }
            throw error;
        }

        return destination.getAbsolutePath();
    }
}
