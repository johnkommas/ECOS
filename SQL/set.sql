/*
 * Copyright (c) Ioannis E. Kommas 2025. All Rights Reserved
 */

UPDATE
    ESFIEinvoiceProviderDetails
SET
    Status =1
WHERE
    fdocumentgid=:unique_id
