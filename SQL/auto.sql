SELECT
    ADCode,
    Status,
    d.fDocumentGID,
    UID,
    AuthenticationCode,
    MarkID,
    ProviderName,
    QRCode,
    InvoiceURL,
    t.ESDCreated,
    t.ESUCreated,
    CurrencyNetValue,
    CurrencyTotalValue,
    CurrencyVATValue,
    fCashAccountTypeCode,
    AuthorizationID,
    StatusText

FROM ESFIEinvoiceProviderDetails d
JOIN ESFIDocumentTrade t
    ON d.fdocumentgid = t.GID
LEFT JOIN ESFILineLiquidityAccount L
    ON t.GID = L.fDocumentGID
LEFT JOIN ESFICashAccount AS CA
            ON L.fLiquidityAccountGID = CA.GID
WHERE Status in (0,2) AND ProviderName = 'Impact'