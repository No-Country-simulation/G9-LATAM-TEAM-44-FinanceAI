package com.financeai.api.exception;

import com.financeai.api.dto.ErrorResponseDTO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponseDTO> handleValidationExceptions(MethodArgumentNotValidException ex) {
        Map<String, String> errores = new HashMap<>();

        for (FieldError error : ex.getBindingResult().getFieldErrors()) {
            errores.put(error.getField(), error.getDefaultMessage());
        }

        ErrorResponseDTO errorResponse = new ErrorResponseDTO(
                "Error de validación en los campos enviados",   // mensaje
                HttpStatus.BAD_REQUEST.value(),                         // codigo_estado
                LocalDateTime.now(),                                    // timestamp
                errores                                                 // detalles
        );

        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(errorResponse);
    }

    /**
     * Red de seguridad. El detalle tecnico va al log, NUNCA al cliente:
     * ex.getMessage() puede filtrar rutas, queries o nombres de clases internos.
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponseDTO> handleGlobalException(Exception ex) {
        log.error("Error no controlado atendiendo la peticion", ex);

        ErrorResponseDTO errorResponse = new ErrorResponseDTO(
                "Ocurrió un error interno en el servidor",
                HttpStatus.INTERNAL_SERVER_ERROR.value(),
                LocalDateTime.now(),
                null
        );

        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
    }
}