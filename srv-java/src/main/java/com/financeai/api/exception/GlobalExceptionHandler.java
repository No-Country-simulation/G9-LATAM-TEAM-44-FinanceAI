package com.financeai.api.exception;

import com.financeai.api.dto.ErrorResponseDTO;
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

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponseDTO> handleGlobalException(Exception ex) {
        ErrorResponseDTO errorResponse = new ErrorResponseDTO(
                ex.getMessage() != null ? ex.getMessage() : "Ocurrió un error interno en el servidor",
                HttpStatus.INTERNAL_SERVER_ERROR.value(),
                LocalDateTime.now(),
                null
        );

        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
    }
}