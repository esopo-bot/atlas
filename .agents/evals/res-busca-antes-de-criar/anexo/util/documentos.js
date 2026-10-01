export function formatarCpf(valor) {
  const digitos = String(valor).replace(/\D/g, '').slice(0, 11);
  return digitos.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
}
