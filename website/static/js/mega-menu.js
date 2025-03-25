document.addEventListener('DOMContentLoaded', () => {
    const menus = [
        { triggerId: 'mens-nav', menuId: 'mega-menu-mens' },
        { triggerId: 'womens-nav', menuId: 'mega-menu-womens' },
        { triggerId: 'gear-nav', menuId: 'mega-menu-gear' }
    ]

    menus.forEach(({ triggerId, menuId }) => {
        const trigger = document.getElementById(triggerId)
        const menu = document.getElementById(menuId)
        let timeout

        trigger.addEventListener('mouseenter', () => {
            clearTimeout(timeout)
            positionMenuBelow(trigger, menu)
            menu.classList.add('show')
        })

        trigger.addEventListener('mouseleave', () => {
            timeout = setTimeout(() => {
                menu.classList.remove('show')
            }, 200)
        })

        menu.addEventListener('mouseenter', () => clearTimeout(timeout))
        menu.addEventListener('mouseleave', () => {
            timeout = setTimeout(() => {
                menu.classList.remove('show')
            }, 200)
        })
    })

    function positionMenuBelow(trigger, menu) {
        const rect = trigger.getBoundingClientRect()
        menu.style.top = rect.bottom + 27 + 'px'
    }
})
