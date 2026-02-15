// 进入全屏
export const enterFullscreen = (el = document.documentElement) => {
  const anyEl = el as any
  if (el.requestFullscreen) el.requestFullscreen()
  else if (anyEl.mozRequestFullScreen) anyEl.mozRequestFullScreen()
  else if (anyEl.webkitRequestFullScreen) anyEl.webkitRequestFullScreen()
  else if (anyEl.msRequestFullscreen) anyEl.msRequestFullscreen()
}

// 退出全屏
export const exitFullscreen = () => {
  const anyDoc = document as any
  if (document.exitFullscreen) document.exitFullscreen()
  else if (anyDoc.mozCancelFullScreen) anyDoc.mozCancelFullScreen()
  else if (anyDoc.webkitExitFullscreen) anyDoc.webkitExitFullscreen()
  else if (anyDoc.msExitFullscreen) anyDoc.msExitFullscreen()
}

// 判断是否全屏
export const isFullscreen = () => {
  const anyDoc = document as any
  const fullscreenElement = 
    document.fullscreenElement ||
    anyDoc.mozFullScreenElement ||
    anyDoc.webkitFullscreenElement ||
    anyDoc.msFullscreenElement ||
    anyDoc.webkitCurrentFullScreenElement
  return !!fullscreenElement
}
