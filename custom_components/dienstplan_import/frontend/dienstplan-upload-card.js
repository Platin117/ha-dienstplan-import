/**
 * Dienstplan upload card — bundled with the Dienstplan Import integration.
 *
 * Reads the chosen .ics file and passes it to the import service over the
 * already authenticated Home Assistant connection (hass.callService). No
 * webhook and no open endpoint required. This file is auto-registered as a
 * frontend resource by the integration, so you only need to add the card:
 *
 *   type: custom:dienstplan-upload-card
 *   title: Import schedule
 *
 * Config options:
 *   title   (string, optional)  Card header. Default: "Import Dienstplan".
 *   service (string, optional)  Service to call. Default: "dienstplan_import.import_ics".
 */

const STYLE = `
  .dp-content { padding: 16px; }
  .dp-filerow { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
  .dp-btn {
    font-family: inherit; font-size: 14px; font-weight: 500;
    border: none; border-radius: 8px; padding: 10px 18px; cursor: pointer;
    transition: opacity .15s ease, background-color .15s ease;
  }
  .dp-btn:disabled { opacity: .5; cursor: not-allowed; }
  .dp-btn-primary { width: 100%; background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .dp-btn-primary:not(:disabled):hover { opacity: .9; }
  .dp-btn-secondary { background: var(--secondary-background-color, rgba(127,127,127,.15)); color: var(--primary-text-color); }
  .dp-fname { color: var(--secondary-text-color); font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .dp-status { margin-top: 14px; min-height: 1.2em; font-size: 14px; line-height: 1.4; }
`;

class DienstplanUploadCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
  }

  getCardSize() {
    return 3;
  }

  _build() {
    this._built = true;
    const title = this._config.title || 'Import Dienstplan';

    this.innerHTML = `
      <ha-card header="${title}">
        <style>${STYLE}</style>
        <div class="dp-content">
          <div class="dp-filerow">
            <input type="file" id="dp-file" accept=".ics,text/calendar" hidden />
            <button class="dp-btn dp-btn-secondary" id="dp-pick" type="button">Choose file</button>
            <span class="dp-fname" id="dp-fname">No file selected</span>
          </div>
          <button class="dp-btn dp-btn-primary" id="dp-import" type="button" disabled>Import</button>
          <div class="dp-status" id="dp-status"></div>
        </div>
      </ha-card>
    `;

    this._file = this.querySelector('#dp-file');
    this._pick = this.querySelector('#dp-pick');
    this._fname = this.querySelector('#dp-fname');
    this._import = this.querySelector('#dp-import');
    this._status = this.querySelector('#dp-status');

    this._pick.addEventListener('click', () => this._file.click());
    this._file.addEventListener('change', () => {
      const f = this._file.files && this._file.files[0];
      this._fname.textContent = f ? f.name : 'No file selected';
      this._import.disabled = !f;
      this._setStatus('');
    });
    this._import.addEventListener('click', () => this._upload());
  }

  _setStatus(text, color) {
    this._status.textContent = text;
    this._status.style.color = color || 'var(--secondary-text-color)';
  }

  async _upload() {
    const file = this._file.files && this._file.files[0];
    if (!file) {
      this._setStatus('Please choose an ICS file first.', 'var(--error-color)');
      return;
    }

    this._import.disabled = true;
    this._setStatus('Reading file…');

    try {
      const text = await file.text();
      if (!text.includes('BEGIN:VCALENDAR')) {
        throw new Error('Not a valid ICS file.');
      }

      this._setStatus('Sending to Home Assistant…');

      const [domain, service] = (this._config.service || 'dienstplan_import.import_ics').split('.');
      await this._hass.callService(domain, service, { ics_content: text });

      this._setStatus('✅ Submitted. The result will appear as a notification.', 'var(--success-color, green)');
      this._file.value = '';
      this._fname.textContent = 'No file selected';
    } catch (err) {
      this._setStatus(`❌ Error: ${err.message}`, 'var(--error-color)');
    } finally {
      this._import.disabled = false;
    }
  }
}

customElements.define('dienstplan-upload-card', DienstplanUploadCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'dienstplan-upload-card',
  name: 'Dienstplan Upload',
  description: 'Uploads an ICS file and imports it into the "Dienstplan" calendar.',
});
