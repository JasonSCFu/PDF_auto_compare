$(document).ready(function() {
    // Handle PDF upload
    $('#upload-form').on('submit', function(e) {
        e.preventDefault();
        var formData = new FormData(this);
        $.ajax({
            url: '/upload',
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function(data) {
                if (data.success) {
                    $('#extract-section').show();
                }
            }
        });
    });

    // Handle page extraction
    $('#extract-form').on('submit', function(e) {
        e.preventDefault();
        var page1 = $('input[name="page1"]').val();
        var page2 = $('input[name="page2"]').val();
        $.post('/extract', { page1: page1, page2: page2 }, function(data) {
            if (data.success) {
                $('#highlight-section').show();
                $('#pdf1-text').text(data.text1);
                $('#pdf2-text').text(data.text2);
            }
        });
    });

    // Highlight selection for PDF 1
    let selectedHighlight1 = '';
    $('#highlight1-btn').on('click', function() {
        var sel = window.getSelection();
        var text = sel.toString();
        if (text) {
            var pre = $('#pdf1-text');
            var highlighted = pre.text().replace(text, '<span class="highlighted">'+text+'</span>');
            pre.html(highlighted);
            selectedHighlight1 = text;
        }
    });

    // Highlight selection for PDF 2
    let selectedHighlight2 = '';
    $('#highlight2-btn').on('click', function() {
        var sel = window.getSelection();
        var text = sel.toString();
        if (text) {
            var pre = $('#pdf2-text');
            var highlighted = pre.text().replace(text, '<span class="highlighted">'+text+'</span>');
            pre.html(highlighted);
            selectedHighlight2 = text;
        }
    });

    // Compare highlights
    // Store original extracted text for reset
    let originalText1 = '';
    let originalText2 = '';

    // After extraction, store the original text
    $('#extract-form').on('submit', function(e) {
        e.preventDefault();
        var page1 = $('input[name="page1"]').val();
        var page2 = $('input[name="page2"]').val();
        $.post('/extract', { page1: page1, page2: page2 }, function(data) {
            if (data.success) {
                $('#highlight-section').show();
                $('#pdf1-text').text(data.text1);
                $('#pdf2-text').text(data.text2);
                originalText1 = data.text1;
                originalText2 = data.text2;
            }
        });
    });

    $('#compare-btn').on('click', function() {
        var text1 = selectedHighlight1;
        var text2 = selectedHighlight2;
        if (!text1 || !text2) {
            alert('Please highlight/select text in both PDFs before comparing.');
            return;
        }
        $.post('/compare', { text1: text1, text2: text2 }, function(data) {
            if (data.success) {
                // Insert diff HTML directly into the extracted text areas
                $('#pdf1-text').html(data.result_html1);
                $('#pdf2-text').html(data.result_html2);
                $('#result-section').show();
                $("#download-btn").attr('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(data.result_text));
            }
        });
    });

    // Reset button handler
    $('#reset-btn').on('click', function() {
        $('#pdf1-text').text(originalText1);
        $('#pdf2-text').text(originalText2);
        selectedHighlight1 = '';
        selectedHighlight2 = '';
        $('#result-section').hide();
    });
});
