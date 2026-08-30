const SPREADSHEET_ID = '1d2fwx0Pbiza3dC39qfE3xw5ukTe43YuxKNv5XxFHacw';
const SYNC_TOKEN = '__SYNC_TOKEN__';

function doGet() {
  return jsonResponse_({ok: true, service: 'Date Detector Sheets Sync'});
}

function doPost(event) {
  try {
    if (!event || !event.postData || !event.postData.contents) {
      throw new Error('Пустой запрос.');
    }

    const payload = JSON.parse(event.postData.contents);
    const expectedToken = SYNC_TOKEN;

    if (!expectedToken || payload.token !== expectedToken) {
      throw new Error('Неверный ключ синхронизации.');
    }
    if (payload.format !== 'date-detector-sqlite-v1') {
      throw new Error('Неподдерживаемый формат базы данных.');
    }

    const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);
    const counts = {};

    (payload.tables || []).forEach(table => {
      const name = String(table.name || '').trim();
      const columns = Array.isArray(table.columns) ? table.columns : [];
      const rows = Array.isArray(table.rows) ? table.rows : [];

      if (!name || !columns.length) {
        return;
      }

      let sheet = spreadsheet.getSheetByName(name);
      if (!sheet) {
        sheet = spreadsheet.insertSheet(name);
      }

      const oldFilter = sheet.getFilter();
      if (oldFilter) {
        oldFilter.remove();
      }
      sheet.clear();

      const values = [columns].concat(rows);
      sheet.getRange(1, 1, values.length, columns.length).setValues(values);
      sheet.setFrozenRows(1);

      const header = sheet.getRange(1, 1, 1, columns.length);
      header
        .setFontWeight('bold')
        .setBackground('#34363D')
        .setFontColor('#FFFFFF');

      if (rows.length) {
        sheet.getRange(1, 1, values.length, columns.length).createFilter();
      }
      sheet.autoResizeColumns(1, Math.min(columns.length, 20));
      counts[name] = rows.length;
    });

    const metaName = 'Синхронизация';
    let meta = spreadsheet.getSheetByName(metaName);
    if (!meta) {
      meta = spreadsheet.insertSheet(metaName);
    }
    meta.clear();
    meta.getRange(1, 1, 3, 2).setValues([
      ['Параметр', 'Значение'],
      ['Последняя выгрузка', payload.exported_at || ''],
      ['Формат', payload.format],
    ]);
    meta.getRange(1, 1, 1, 2)
      .setFontWeight('bold')
      .setBackground('#34363D')
      .setFontColor('#FFFFFF');
    meta.setFrozenRows(1);
    meta.autoResizeColumns(1, 2);

    SpreadsheetApp.flush();
    return jsonResponse_({ok: true, counts: counts});
  } catch (error) {
    return jsonResponse_({ok: false, error: String(error.message || error)});
  }
}

function jsonResponse_(payload) {
  return ContentService
    .createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}
