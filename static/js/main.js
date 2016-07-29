(function () {
    var map, markerCache = {};

    // Label countdown
    (function () {
        function zeroPad(n) {
            return ('0' + n).slice(-2);
        }

        function setLabelTime() {
            $('.label-countdown').each(function (index, element) {
                var difference, minutes, seconds, timestring,
                    disappearsAt = new Date(parseInt(
                        element.getAttribute('disappears-at')
                    ));

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

        window.setInterval(setLabelTime, 1000);
    })();

    // Controls what pokemon are displayed
    var Displayed = (function () {
        var hiddenPokemon = JSON.parse(
            localStorage.getItem('hiddenPokemon') || '[]'
        );

        function saveState() {
            localStorage.setItem(
                'hiddenPokemon', JSON.stringify(hiddenPokemon)
            );
        }

        function getHiddenPokemon() {
            return hiddenPokemon;
        }

        function isDisplayed(pokemonNumber) {
            return hiddenPokemon.indexOf(pokemonNumber) === -1;
        }

        function addPokemon(pokemonNumber) {
            hiddenPokemon.splice(hiddenPokemon.indexOf(pokemonNumber), 1);
        }

        function removePokemon(pokemonNumber) {
            hiddenPokemon.push(pokemonNumber);
            saveState();
        }

        return {
            getHiddenPokemon: getHiddenPokemon,
            isDisplayed: isDisplayed,
            addPokemon: addPokemon,
            removePokemon: removePokemon
        };
    })();

    function createMap() {
        var center = new google.maps.LatLng(
            window.POGO.origin_lat, window.POGO.origin_lng
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

    var INFOBOX_TEMPLATE = [
        '<div><b>NAME</b></div>',
        '<div>Disappears at - TIME ',
        '<span class="label-countdown" disappears-at="EXPIRES_AT_MS"></span>',
        '</div>'
    ].join('');

    function makeInfoBox(item) {
        var date = new Date(item.disappear_time),
            formattedDate = date.getHours() + ':' + date.getMinutes() + ':' + date.getSeconds();
        return (
            INFOBOX_TEMPLATE
                .replace(/NAME/g, window.POGO.pokemon[item.pokemon])
                .replace(/TIME/g, formattedDate)
                .replace(/EXPIRES_AT_MS/g, item.disappear_time)
        );
    }

    function addMarker(item) {
        if (item.key in markerCache || !Displayed.isDisplayed(item.pokemon)) {
            return;
        }

        var disappearsMs = new Date(item.disappear_time) - new Date();
        if (disappearsMs < 0) {
            return;
        }
        var marker = new google.maps.Marker({
            position: new google.maps.LatLng(item.lat, item.lng),
            map: map,
            icon: '/static/icons/' + item.pokemon + '.png'
        });
        markerCache[item.key] = marker;

        var infoWindow = new google.maps.InfoWindow({
            content: makeInfoBox(item)
        });
        marker.addListener('click', infoWindow.open.bind(infoWindow, map, marker));

        marker.pokemon = item.pokemon;
        marker.interval = window.setTimeout(
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

    // Modal functionality
    var Modal = (function () {
        var body = $('body');

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

        function showModal(modalElement, e) {
            body.addClass('modal-visible');
            modalElement.removeClass('hidden');
            e.stopPropagation();
        }

        body.on('click', maybeHideModals);
        $(window).on('keyup', handleKeypress);

        return {showModal: showModal};
    })();

    // Settings modal
    (function () {
        var num,
            settingsModal = $('.modal-settings'),
            search = settingsModal.find('.search'),
            results = settingsModal.find('.search-results'),
            POKEMON_TEMPLATE = [
                '<tr>',
                '<td><img src="static/icons/NUMBER.png"></td>',
                '<td>#NUMBER</td>',
                '<td>NAME</td>',
                '<td><label>',
                '<input ',
                '    type="checkbox" ',
                '    class="displayed" ',
                '    value="NUMBER"',
                '    CHECKED',
                '> display</label></td>',
                '</tr>'
            ].join('');

        function getPokemonFromText(text) {
            var i, name, ret = [], asNumber = parseInt(text, 10);

            if (1 <= asNumber && asNumber <= 151) {
                ret.push(asNumber);
            } else if (text) {
                for (i = 0; i < window.POGO.pokemon.length; i += 1) {
                    name = window.POGO.pokemon[i].toLowerCase();
                    if (name.indexOf(text) === 0) {
                        ret.push(i);
                    }
                }
            }
            return ret;
        }

        function toPokemonInput(number) {
            var checked = Displayed.isDisplayed(number) ? 'checked' : '';
            return (
                POKEMON_TEMPLATE
                    .replace(/NUMBER/g, number.toString(10))
                    .replace(/NAME/g, window.POGO.pokemon[number])
                    .replace(/CHECKED/g, checked)
            );
        }

        function filterPokemon() {
            var i, parts = [], toDisplay = getPokemonFromText(
                search.val().trim().toLowerCase()
            );
            if (!toDisplay.length) {
                results.text('No results.');
            } else {
                parts.push('<table>');
                for (i = 0; i < toDisplay.length; i += 1) {
                    parts.push(toPokemonInput(toDisplay[i]));
                }
                parts.push('</table>');
                results.html(parts.join(''));
            }
        }

        function changeDisplayed(e) {
            var k, marker,
                target = $(e.target),
                number = parseInt(target.val(), 10);

            if (target.is(':checked')) {
                Displayed.addPokemon(number);
                updateMap();
            } else {
                Displayed.removePokemon(number);
                // Remove all displayed markers of that pokemon
                Object.keys(markerCache).forEach(function (k) {
                    marker = markerCache[k];
                    if (marker.pokemon === number) {
                        window.clearInterval(marker.interval);
                        marker.setMap(null);
                        delete markerCache[k];
                    }
                });
            }
        }

        search.val('');
        search.on('keyup', filterPokemon);

        settingsModal.delegate('.displayed', 'change', changeDisplayed);

        $('.settings').on('click', Modal.showModal.bind(null, settingsModal));
    })();

    // About modal
    (function () {
        var aboutModal = $('.modal-about');
        $('.about').on('click', Modal.showModal.bind(null, aboutModal));
    })();

    window.initMap = function () {
        createMap();
        updateMap();
        $('.refresh').on('click', updateMap);
        if (window.POGO.auto_refresh) {
            window.setInterval(updateMap, window.POGO.auto_refresh);
        }
    }
})();
