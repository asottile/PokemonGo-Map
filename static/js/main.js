(function () {
    var map, markerCache = {}, body = $('body');

    function zeroPad(n) {
        return ('0' + n).slice(-2);
    }

    function setLabelTime() {
        $('.label-countdown').each(function (index, element) {
            var difference, minutes, seconds, timestring,
                disappearsAt = new Date(parseInt(element.getAttribute('disappears-at')));

            difference = disappearsAt - new Date();
            if (difference < 0) {
                timestring = '(expired)';
            } else {
                minutes = Math.floor(difference / (60 * 1000));
                difference %= (60 * 1000);
                seconds = Math.floor(difference / 1000);

                timestring = [
                    '(', zeroPad(minutes), 'm', zeroPad(seconds), 's', ')'
                ].join('');
            }

            $(element).text(timestring)
        });
    };

    function createMap() {
        var center = new google.maps.LatLng(
            window.POGO.originLat, window.POGO.originLng
        );
        map = new google.maps.Map(
            document.getElementById('fullmap'), {
                center: center,
                zoom: window.POGO.zoom,
                mapTypeId: google.maps.MapTypeId.ROADMAP,
                zoomControl: true,
                mapTypeControl: true,
                scaleControl: true,
                streetViewControl: true,
                rotateControl: true,
                fullscreenControl: true
        });
        new google.maps.Marker({
            position: center,
            map: map,
            icon: '//maps.google.com/mapfiles/ms/icons/red-dot.png'
        });
    }

    function addMarker(item) {
        if (item.key in markerCache) {
            return;
        }

        var disappearsMs = new Date(item.disappear_time) - new Date();
        if (disappearsMs < 0) {
            return;
        }
        var marker = new google.maps.Marker({
            position: new google.maps.LatLng(item.lat, item.lng),
            map: map,
            icon: item.icon,
        });
        markerCache[item.key] = marker;

        var infoWindow = new google.maps.InfoWindow({content: item.infobox});
        marker.addListener('click', infoWindow.open.bind(infoWindow, map, marker));

        window.setTimeout(
            function () {
                markerCache[item.key].setMap(null);
                delete markerCache[item.key];
            },
            disappearsMs
        );
    }

    function updateMap() {
        $.get('/data', function(data) {
            for (var i = 0; i < data.length; i += 1) {
                addMarker(data[i]);
            }
        });
    }

    function showModal(modalElement, e) {
        body.addClass('modal-visible');
        modalElement.removeClass('hidden');
        e.stopPropagation();
    }

    function maybeHideModals(e) {
        if ($(e.target).is('.modal-visible')) {
            body.removeClass('modal-visible');
            $('.modal').addClass('hidden');
        }
    }

    function handleKeypress(e) {
        if (e.which === 27) {
            maybeHideModals(e);
        }
    }

    window.initMap = function () {
        createMap();
        updateMap();
        $('.refresh').on('click', updateMap);
        $('.about').on('click', showModal.bind(null, $('.modal-about')));
        body.on('click', maybeHideModals);
        $(window).on('keyup', handleKeypress);
        if (window.POGO.autoRefresh) {
            window.setInterval(updateMap, window.POGO.autoRefresh);
        }
    }

    window.setInterval(setLabelTime, 1000);
})();
