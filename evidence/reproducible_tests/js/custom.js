$(function () {
  new Nanobar().go(100);

  $('[data-toggle="tooltip"]').tooltip()

  $('.navbar-collapse').on('hide.bs.collapse', function () {
    $('.hamburger').stop().removeClass('is-active');
  })
  $('.navbar-collapse').on('show.bs.collapse', function () {
    $('.hamburger').stop().addClass('is-active');
  })

  $('.credit-mobile-box, .credit-desktop-box').click(function() {
    var that = $(this)
    that.css('min-width', that.innerWidth())
    that.find('.fa-sync-alt').addClass('d-none')
    that.find('a').removeClass('pulse')
    $.ajax({
      url: '/member/clear-credit-cache/'+$(this).data('id'),
      beforeSend: function(){
         that.find('.credit').html('<i class="fas fa-sync-alt fa-spin"></i>')
      }
    }).done(function(credit) {
       setTimeout(function(){
         that.find('.fa-sync-alt').removeClass('d-none')
         that.find('span.credit').html(credit)
         that.find('a').css('display','none').addClass('animated pulse').css('display','block')
       }, 1000)
    })

  });

  // $('input[name="switch-theme"], input[name="switch-theme-sp"]').on('click', function() {
  //   var currentTheme = $(this).prop('checked') ? 'theme-light':'theme-dark'
  //   $.ajax({
  //     url: '/member/theme/'+currentTheme,
  //   })
  // });

  var doubleTouchStartTimestamp = 0;
  $(document).bind("touchstart", function(event){
      var now = +(new Date());
      if (doubleTouchStartTimestamp + 500 > now){
          event.preventDefault();
      };
      doubleTouchStartTimestamp = now;
  });

  // var pusher = new Pusher(window.Config.PUSH_KEY, {
  //   cluster: 'ap1',
  //   encrypted: true
  // });
  //
  // var notifyFunction = function(data){
  //     // data.message
  //     (new PNotify({
  //         title: 'คุณมีข้อความใหม่',
  //         text: data.message.title,
  //         addclass: "stack-bottomright",
  //         icon: 'fa fa-envelope-o',
  //         desktop: {
  //             desktop: true,
  //             icon: '/assets/imgs/pnotify/default.png',
  //         },
  //     })).get().click(function(e) {
  //         if ($('.ui-pnotify-closer, .ui-pnotify-sticker, .ui-pnotify-closer *, .ui-pnotify-sticker *').is(e.target)) return;
  //         $(location).attr('href', '/member/messages/'+data.message.id)
  //     });
  // }
  //
  // var channel = pusher.subscribe('notify-message');
  // channel.bind('user-id-'+window.Config.USERID, function(data) { notifyFunction(data) });
  // channel.bind('alluser', function(data) { notifyFunction(data) });
  // channel.bind('agent-'+window.Config.AGENTUSERID, function(data) { notifyFunction(data) });


  // $.idleTimeout('#idle-timeout-dialog', '.modal-content button:last', {
  //   idleAfter: 3600, // 5 seconds - dafault 900
  //   timeout: 30000, //30 seconds to timeout
  //   pollingInterval: 500, // 5 seconds
  //   keepAliveURL: SITE_SECTION_URL +'/misc/keepalive',
  //   serverResponseEquals: 'OK',
  //   onTimeout: function(){
  //       window.location = SITE_URL + "/user/logout";
  //   },
  //   onIdle: function(){
  //     $('#idle-timeout-dialog').modal('show');
  //     $(".modal-backdrop").css("z-index", "1500");
  //     $countdown = $('#idle-timeout-counter');
  //
  //     $('#idle-timeout-dialog-keepalive').on('click', function () {
  //         $('#idle-timeout-dialog').modal('hide');
  //     });
  //
  //     $('#idle-timeout-dialog-logout').on('click', function () {
  //         $('#idle-timeout-dialog').modal('hide');
  //         $.idleTimeout.options.onTimeout.call(this);
  //     });
  //   },
  //   onCountdown: function(counter){
  //       $countdown.html(counter); // update the counter
  //   }
  // });

})
