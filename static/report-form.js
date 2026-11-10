(function () {
  'use strict';
  const reportForm = document.querySelector('#report-form');
  const attachmentForm = document.querySelector('#attachment-form');
  if (!reportForm) return;

  let dirty = false;
  let submittingReport = false;
  const markDirty = () => { dirty = true; };
  reportForm.addEventListener('input', markDirty);
  reportForm.addEventListener('change', markDirty);
  reportForm.addEventListener('submit', () => { submittingReport = true; });

  if (attachmentForm) {
    attachmentForm.addEventListener('submit', event => {
      if (!dirty) return;
      event.preventDefault();
      window.alert('Rapporten har osparade ändringar. Spara utkastet innan du laddar upp bilagan.');
    });
  }

  window.addEventListener('beforeunload', event => {
    if (!dirty || submittingReport) return;
    event.preventDefault();
    event.returnValue = '';
  });
})();
