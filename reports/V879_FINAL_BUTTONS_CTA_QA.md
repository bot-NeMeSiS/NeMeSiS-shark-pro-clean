# V879 Final Buttons CTA QA

## Reglas aplicadas

- Label visible una vez.
- Máximo recomendado: una acción principal y una secundaria por card.
- Acciones con wrapping seguro.
- No se permite `Ver Ver`, `Abrir Abrir`, `SHARK SHARK`, `Telegram Telegram` ni `Panel Panel`.
- Admin y cliente mantienen navegación separada.

## Corrección V879

El CSS V879 normaliza `.ns-button`, `.action-button` y acciones en cards para reducir botones gigantes, duplicados visuales y overflow.

## Validación

El check V879 revisa duplicados evidentes en textos interactivos de templates primarios.
