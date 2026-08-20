package com.financeai.api.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

import java.util.List;

/**
 * Peticion de analisis financiero.
 *
 * Las restricciones estan alineadas con el contrato de srv-python (app/main.py)
 * para que lo que alli seria un 422 opaco se rechace aqui con un 400 y un
 * mensaje por campo. Si cambia un limite, hay que cambiarlo en los dos sitios.
 */
public record FinancialAnalysisRequestDTO(

        // Python: ingreso_mensual = Field(gt=0)
        @NotNull(message = "El ingreso mensual es requerido")
        @Positive(message = "El ingreso mensual debe ser mayor a 0")
        Double ingresoMensual,

        // Python: nivel_endeudamiento = Field(ge=0, le=100)
        @NotNull(message = "El nivel de endeudamiento es requerido")
        @Min(value = 0, message = "El nivel de endeudamiento no puede ser negativo")
        @Max(value = 100, message = "El nivel de endeudamiento es un porcentaje: maximo 100")
        Integer nivelEndeudamiento,

        // Python: validator acepta Alta, Media, Baja o Nula (sin importar mayusculas)
        @NotNull(message = "La frecuencia de ahorro es requerida")
        @Pattern(regexp = "(?i)^(alta|media|baja|nula)$",
                message = "La frecuencia de ahorro debe ser Alta, Media, Baja o Nula")
        String frecuenciaAhorro,

        // Python: transacciones = Field(min_length=1, max_length=5000)
        @NotNull(message = "La lista de transacciones es requerida")
        @Size(min = 1, max = 5000, message = "Se requiere entre 1 y 5000 transacciones")
        @Valid
        List<TransactionDTO> transacciones
) {}
